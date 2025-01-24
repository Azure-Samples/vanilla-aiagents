from typing import Annotated
import unittest
import os, logging, sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.user import User
from vanilla_aiagents.team import Team
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv

load_dotenv(override=True)


class TestAgent(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM(
            {
                "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_KEY"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
            }
        )

        logging.basicConfig(level=logging.INFO)
        logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.llm").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.team").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.workflow").setLevel(logging.DEBUG)

    def test_workflow_run_streaming(self):
        agent1 = Agent(
            id="agent1",
            llm=self.llm,
            description="Call this agent for general purpose questions",
            system_message="""You are an AI assistant
            Your task is to help the user with their questions.
            Always respond with the best answer you can generate.
            If you don't know the answer, respond with "I don't know".
            Always be polite and helpful.
            """,
        )

        @agent1.register_tool(
            description="Get the order ID for a customer's order. Call this whenever you need to know the order ID, for example when a customer asks 'Where is my package'"
        )
        def get_order_id() -> Annotated[str, "The customer's order ID."]:
            return "214"

        @agent1.register_tool(
            description="Get the delivery date for a customer's order. Call this whenever you need to know the delivery date, for example when a customer asks 'Where is my package'"
        )
        def get_delivery_date(
            order_id: Annotated[str, "The customer's order ID."]
        ) -> Annotated[str, "The delivery date for the customer's order."]:
            return "2022-01-01"

        user = User(id="user", mode="unattended")

        team = Team(
            id="team",
            description="",
            members=[agent1, user],
            llm=self.llm,
            stop_callback=lambda conv: len(conv.messages) > 4,
        )
        workflow = Workflow(askable=team)

        stack_count = 0
        for mark, content in workflow.run_stream(
            "Which is expected delivery date for my order? Use format like February 1, 2022"
        ):
            logging.debug(f"Mark: {mark}, Content: {content}")
            if mark == "start":
                stack_count += 1
                if stack_count == 1:
                    self.assertEqual(
                        content,
                        team.id,
                        f"Expected {team.id} for start mark at stack count 1",
                    )
                if stack_count == 2:
                    self.assertEqual(
                        content,
                        agent1.id,
                        f"Expected {agent1.id} for start mark at stack count 2",
                    )
            elif mark == "end":
                stack_count -= 1
                if stack_count == 1:
                    self.assertEqual(
                        content,
                        agent1.id,
                        f"Expected {agent1.id} for end mark at stack count 1",
                    )
                if stack_count == 0:
                    self.assertEqual(
                        content,
                        team.id,
                        f"Expected {team.id} for end mark at stack count 0",
                    )
                    break
            elif mark == "response":
                self.assertIn(
                    "January 1, 2022",
                    content[0]["content"],
                    "Expected delivery date not found in the response",
                )

        self.assertIn(
            "January 1, 2022",
            workflow.conversation.messages[-1]["content"],
            "Expected delivery date not found in the conversation messages",
        )


if __name__ == "__main__":
    unittest.main()
