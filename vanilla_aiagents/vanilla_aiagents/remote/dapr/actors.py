import json
import os
import importlib.util
from typing import Type, Union
from dapr.actor import ActorInterface, Actor, actormethod
from dapr.clients import DaprClient
from pydantic import BaseModel

from vanilla_aiagents.askable import Askable
from vanilla_aiagents.conversation import Conversation
from vanilla_aiagents.workflow import Workflow
import logging

logger = logging.getLogger(__name__)
PUBSUB_NAME = os.getenv("PUBSUB_NAME", "workflow")
TOPIC_NAME = os.getenv("TOPIC_NAME", "events")


class WorkflowRunResult(BaseModel):
    result: str = ""
    messages: list[dict] = []


class WorkflowActorInterface(ActorInterface):
    @actormethod(name="run")
    async def run(self, workflow_input: Union[str, dict]) -> dict: ...

    @actormethod(name="run_stream")
    async def run_stream(self, workflow_input: Union[str, dict]) -> None: ...

    @actormethod(name="get_conversation")
    async def get_conversation(self) -> dict: ...


class WorkflowActor(Actor, WorkflowActorInterface):
    workflow: Workflow
    askable_type: Type[Askable]

    async def _on_activate(self) -> None:
        # Load state on activation
        (exists, state) = await self._state_manager.try_get_state("conversation")

        # Dynamically import the module and class from a local file
        source_dir = os.curdir
        file_path = os.path.join(source_dir, "_actor_askable.py")
        module_name = "_actor_askable"
        logger.info(f"Loading askable from {file_path}")

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        askable_class = getattr(module, "_actor_askable")
        logger.info(f"Loaded askable: {askable_class}")

        self.workflow = Workflow(
            askable=askable_class,
            conversation=Conversation.from_dict(state if state is not None else {}),
        )

    async def get_conversation(self) -> dict:
        logger.debug(f"Getting conversation for {self.id}")
        return self.workflow.conversation.to_dict()

    async def run(self, workflow_input: Union[str, dict]) -> dict:
        run_result = WorkflowRunResult(result="", messages=[])

        try:
            n = len(self.workflow.conversation.messages)
            run_result.result = self.workflow.run(workflow_input)
            run_result.messages = self.workflow.conversation.messages[n + 1 :]

            if run_result.result == "agent-stop":
                self._notify_stop()

            # Save state
            await self._save_conversation()
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            run_result.result = str(e)

        return run_result.model_dump()

    async def run_stream(self, workflow_input: Union[str, dict]):
        result: str = None
        with DaprClient() as client:
            async for [mark, content] in self.workflow.run_stream(workflow_input):
                client.publish_event(
                    pubsub_name=PUBSUB_NAME,
                    topic_name=TOPIC_NAME,
                    data_content_type="application/json",
                    data=json.dumps(
                        {
                            "source": str(self.id),
                            "mark": mark,
                            "content": content,
                        }
                    ),
                    publish_metadata={
                        "source": str(self.id),
                        "type": "stream",
                    },
                )

                if mark == "result":
                    result = content

            if result == "agent-stop":
                self._notify_stop()

            await self._save_conversation()

    async def _save_conversation(self):
        logger.debug("Saving conversation state")
        await self._state_manager.set_state(
            "conversation", self.workflow.conversation.to_dict()
        )
        await self._state_manager.save_state()

        logger.debug("Publishing conversation update event")
        with DaprClient() as client:
            client.publish_event(
                PUBSUB_NAME,
                TOPIC_NAME,
                publish_metadata={
                    "id": str(self.id),
                    "type": "update",
                },
                data_content_type="application/json",
                data=json.dumps(
                    {
                        "id": str(self.id),
                        "type": "update",
                    }
                ),
            )
        logger.debug("Conversation state saved and event published")

    def _notify_stop(self):
        # Retrieve which askable stopped the conversation
        (level, kind, agent) = next(
            (l, k, a)
            for (l, k, a) in reversed(self.workflow.conversation.log)
            if k == "agent/stop"
        )
        logger.info(f"Got stop signal from '{agent}'. Publishing stop event")
        with DaprClient() as client:
            client.publish_event(
                PUBSUB_NAME,
                TOPIC_NAME,
                publish_metadata={
                    "id": str(self.id),
                    "source": agent,
                    "type": "stop",
                },
                data_content_type="application/json",
                data=json.dumps(
                    {
                        "id": str(self.id),
                        "source": agent,
                        "type": "stop",
                        "conversation": self.workflow.conversation.to_dict(),
                    }
                ),
            )
        logger.debug("Stop event published")
