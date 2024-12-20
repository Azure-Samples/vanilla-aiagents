from vanilla_aiagents.conversation import Conversation
from .askable import Askable
from .llm import LLM

import logging

logger = logging.getLogger(__name__)


class Sequence(Askable):
    """A sequence of Askable steps that are ALWAYS asked in order."""

    def __init__(
        self,
        llm: LLM,
        description: str,
        id: str,
        steps: list[Askable],
        system_prompt: str = "",
    ):
        """
        Initialize the Sequence object.

        Args:
            llm (LLM): The language model to use for the decision-making process.
            description (str): The description of the Sequence object.
            id (str): The ID of the Sequence object. Will be used to uniquely identify it.
            steps (list[Askable]): The steps that are part of the sequence.
            system_prompt (str): The system prompt to use for the sequence.
        """
        super().__init__(id, description)
        self.steps = steps
        self.system_prompt = system_prompt

        self.llm = llm

        logger.debug(
            "[Sequence %s] initialized with agents: %s",
            self.id,
            [step.id for step in self.steps],
        )

    def ask(self, conversation: Conversation, stream=False):

        execution_result = None
        if stream:
            conversation.update(["start", self.id])
        for step in self.steps:
            agent_result = step.ask(conversation, stream=stream)
            logger.debug(
                "[Sequence %s] asked step '%s' with messages: %s",
                self.id,
                step.id,
                agent_result,
            )

            if agent_result == "stop":
                logger.debug(
                    "[Sequence %s] stop signal received, ending workflow.", self.id
                )
                execution_result = "agent-stop"
                break
            elif agent_result == "error":
                logger.error(
                    "[Sequence %s] error signal received, ending workflow.", self.id
                )
                execution_result = "agent-error"
                break

        if stream:
            conversation.update(["end", self.id])

        return execution_result
