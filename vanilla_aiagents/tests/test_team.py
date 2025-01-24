from typing import Annotated
import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.team import Team
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv

load_dotenv(override=True)


class TestTeam(unittest.TestCase):

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
        logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.team").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.workflow").setLevel(logging.DEBUG)

    def test_transitions(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(
            id="first",
            llm=self.llm,
            description="Agent that sets context variables",
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
            description="Agent that uses context variables to answer",
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
            allowed_transitions={first: [second]},
            stop_callback=lambda conv: len(conv.messages) > 3,
        )
        workflow = Workflow(askable=flow)
        workflow.restart()

        workflow.run("Which channel is this conversation on?")

        self.assertEqual(
            len(workflow.conversation.messages),
            4,
            "Expected 3 messages in the conversation",
        )

        self.assertIn(
            "Context set",
            workflow.conversation.messages[2]["content"],
            "Expected context to be set",
        )
        self.assertIn(
            "voice",
            workflow.conversation.messages[3]["content"],
            "Expected second agent to recognize context variable CHANNEL",
        )

    def test_use_tools(self):
        first = Agent(
            id="first",
            llm=self.llm,
            description="Agent1",
            system_message="""You are part of an AI process
        Your task is to support the user inquiry by providing the user profile.
        """,
        )

        @first.register_tool(
            name="get_user_profile", description="Get the user profile"
        )
        def get_user_profile():
            return 'User profile: {"name": "John", "age": 30}'

        second = Agent(
            id="second",
            llm=self.llm,
            description="Agent2",
            system_message="""You are part of an AI process
        Your task is to support the user inquiry by providing the user balance.
        """,
        )

        @second.register_tool(
            name="get_user_balance", description="Get the user balance"
        )
        def get_user_balance():
            return "User balance: $100"

        flow = Team(
            id="flow",
            description="",
            members=[first, second],
            llm=self.llm,
            stop_callback=lambda conv: len(conv.messages) > 3,
            include_tools_descriptions=True,
        )
        workflow = Workflow(askable=flow)
        workflow.restart()

        workflow.run("Which is my current balance?")

        # Assert the last message in the conversation is the user balance
        self.assertEqual(
            second.id,
            workflow.conversation.messages[-1]["name"],
            "Expected user balance to be provided",
        )

    def test_not_use_structured_output(self):
        first = Agent(
            id="first",
            llm=self.llm,
            description="Agent1",
            system_message="""You are part of an AI process
        Your task is to support the user inquiry.
        """,
        )

        @first.register_tool(
            name="get_user_profile", description="Get the user profile"
        )
        def get_user_profile() -> (
            Annotated[str, "The user profile, containing name and age"]
        ):
            return 'User profile: {"name": "John", "age": 30}'

        second = Agent(
            id="second",
            llm=self.llm,
            description="Agent2",
            system_message="""You are part of an AI process
        Your task is to support the user inquiry.
        """,
        )

        @second.register_tool(
            name="get_user_balance", description="Get the user balance"
        )
        def get_user_balance() -> Annotated[str, "The user balance in USD"]:
            return "User balance: $100"

        flow = Team(
            id="flow",
            description="",
            members=[first, second],
            llm=self.llm,
            stop_callback=lambda conv: len(conv.messages) == 3,
            include_tools_descriptions=True,
            use_structured_output=False,
        )
        workflow = Workflow(askable=flow)
        workflow.restart()

        workflow.run("Which is my current balance?")

        # Assert the last message in the conversation is the user balance
        self.assertEqual(
            second.id,
            workflow.conversation.messages[-1]["name"],
            "Expected user balance to be provided",
        )


if __name__ == "__main__":
    unittest.main()
