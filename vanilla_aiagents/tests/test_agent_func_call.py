from typing import Annotated
import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.user import User
from vanilla_aiagents.team import Team
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv
load_dotenv(override=True)

class TestAgent(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })
        
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.llm").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.team").setLevel(logging.DEBUG)

    def test_func_call(self):
        agent1 = Agent(id="agent", llm=self.llm, description="Call this agent to answer questions by the user. This agent can answer about accounts", system_message = """You are an AI assistant
        Your task is to help the user with their questions.
        Always respond with the best answer you can generate.
        If you don't know the answer, respond with "I don't know".
        Always be polite and helpful.
        """)
        
        @agent1.register_tool(description="get user balance")
        def get_user_balance() -> Annotated[str, "The user balance in USD"]:
            return "100"

        user = User(id="user", mode="unattended")
        
        flow = Team(id="team", description="", members=[agent1, user], llm=self.llm, stop_callback=lambda msgs: len(msgs) > 6)
        workflow = Workflow(askable=flow)
        
        workflow.run("Hi! Which is my account balance?")
        
        self.assertGreaterEqual(len(workflow.conversation.messages), 3, "Expected at least 3 messages in the conversation")
        self.assertEqual(workflow.conversation.messages[-1]["name"], "agent", "Expected agent to respond with greeting")
        self.assertIn("100", workflow.conversation.messages[-1]["content"], "Expected agent to respond with balance 100$")
    
    def test_multiple_func_call(self):
        agent1 = Agent(id="agent", llm=self.llm, description="Call this agent to play guess the number game with the use", system_message = """You are an AI assistant
        Your task is to play a game with the user.
        You first generate a random number between 1 and 100. Then save it as a conversation variable named "number".
        The user will try to guess the number.
        If the user's guess is too high, respond with "Too high".
        If the user's guess is too low, respond with "Too low".
        """)
        
        @agent1.register_tool(description="Generate a random number")
        def random() -> Annotated[str, "A random number"]:
            # Better to use a fixed number for testing
            return "42"

        user = User(id="user", mode="unattended")
        
        flow = Team(id="team", description="", members=[agent1, user], llm=self.llm, stop_callback=lambda msgs: len(msgs) > 2)
        workflow = Workflow(askable=flow)
        
        workflow.run("Hi! Let's play a game. Guess the number.")
        
        self.assertIn("number", workflow.conversation.variables, "Expected agent to have generated and saved a random number")
        self.assertEqual(workflow.conversation.variables["number"], "42", "Expected agent to have generated and saved a random number")


if __name__ == '__main__':
    unittest.main()