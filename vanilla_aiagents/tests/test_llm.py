import unittest
import os, logging, sys

from pydantic import BaseModel

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.sequence import Sequence
from vanilla_aiagents.llm import AzureOpenAILLM, LLMConstraints
from vanilla_aiagents.team import Team

from dotenv import load_dotenv

load_dotenv(override=True)


class TestLLM(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM(
            {
                "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_KEY"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
            }
        )

        # Set logging to debug for Agent, User, and Workflow
        logging.basicConfig(level=logging.INFO)
        # logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        # logging.getLogger("vanilla_aiagents.user").setLevel(logging.DEBUG)
        # logging.getLogger("vanilla_aiagents.workflow").setLevel(logging.DEBUG)

    def test_metrics_sequence(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(
            id="first",
            llm=self.llm,
            description="First agent",
            system_message="""You are part of an AI process
        Your task is to set a context for the next agent to continue the conversation.

        DO set context variable "CHANNEL" to "voice" and "LANGUAGE" to "en"

        DO respond only "Context set" when you are done.
        """,
        )

        # Second agent might have its system message extended automatically with the context from the ongoing conversation
        second = Agent(
            id="second",
            llm=self.llm,
            description="Second agent",
            system_message="""You are part of an AI process
        Your task is to continue the conversation based on the context set by the previous agent.
        When asked, you can use variable provide in CONTEXT to generate the response.

        --- CONTEXT ---
        __context__
        """,
        )

        flow = Sequence(id="flow", description="", steps=[first, second], llm=self.llm)
        workflow = Workflow(askable=flow)

        workflow.run("Which channel is this conversation on?")

        self.assertGreater(
            workflow.conversation.metrics.completion_tokens,
            0,
            "Expected completion_tokens to be greater than 0",
        )
        self.assertGreater(
            workflow.conversation.metrics.prompt_tokens,
            0,
            "Expected prompt_tokens to be greater than 0",
        )
        self.assertGreater(
            workflow.conversation.metrics.total_tokens,
            0,
            "Expected total_tokens to be greater than 0",
        )

    def test_metrics_team(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(
            id="first",
            llm=self.llm,
            description="First agent",
            system_message="""You are part of an AI process
        Your task is to set a context for the next agent to continue the conversation.

        DO set context variable "CHANNEL" to "voice" and "LANGUAGE" to "en"

        DO respond only "Context set" when you are done.
        """,
        )

        # Second agent might have its system message extended automatically with the context from the ongoing conversation
        second = Agent(
            id="second",
            llm=self.llm,
            description="Second agent",
            system_message="""You are part of an AI process
        Your task is to continue the conversation based on the context set by the previous agent.
        When asked, you can use variable provide in CONTEXT to generate the response.

        --- CONTEXT ---
        __context__
        """,
        )

        flow = Team(
            id="flow",
            description="",
            members=[first, second],
            llm=self.llm,
            stop_callback=lambda conv: len(conv.messages) > 2,
        )
        workflow = Workflow(askable=flow)

        workflow.run("Which channel is this conversation on?")

        self.assertGreater(
            workflow.conversation.metrics.completion_tokens,
            0,
            "Expected completion_tokens to be greater than 0",
        )
        self.assertGreater(
            workflow.conversation.metrics.prompt_tokens,
            0,
            "Expected prompt_tokens to be greater than 0",
        )
        self.assertGreater(
            workflow.conversation.metrics.total_tokens,
            0,
            "Expected total_tokens to be greater than 0",
        )

    def test_constraints(self):
        llm2 = AzureOpenAILLM(
            {
                "azure_deployment": "o1-mini",
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_KEY"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
            },
            constraints=LLMConstraints(
                temperature=1, structured_output=False, system_message=False
            ),
        )

        class HelloResponse(BaseModel):
            response: str

        response, metrics = llm2.ask(
            messages=[
                {
                    "role": "system",
                    "content": """Say hello with JSON format {response: "message"}""",
                }
            ],
            response_format=HelloResponse,
            temperature=0.7,
        )

        # If this call passes, then the constraints are working
        self.assertIsNotNone(response, "Expected response to be not None")


if __name__ == "__main__":
    unittest.main()
