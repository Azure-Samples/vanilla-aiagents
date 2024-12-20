import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.conversation import Conversation
from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.user import User
from vanilla_aiagents.team import Team
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv
load_dotenv(override=True)

class TestUser(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })
        
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.user").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.team").setLevel(logging.DEBUG)

    def test_user(self):
        agent1 = Agent(id="agent", llm=self.llm, description="Call this agent to answer questions by the user", system_message = """You are an AI assistant
        Your task is to help the user with their questions.
        Always respond with the best answer you can generate.
        If you don't know the answer, respond with "I don't know".
        Always be polite and helpful.
        """)

        user = User(id="user", mode="unattended")
        
        flow = Team(id="team", description="", members=[agent1, user], llm=self.llm, stop_callback=lambda msgs: len(msgs) > 6)
        workflow = Workflow(askable=flow)
        
        workflow.run("Hi! Can you help me with capital cities?")
        
        self.assertEqual(len(workflow.conversation.messages), 3, "Expected 3 messages in the conversation")
        self.assertEqual(workflow.conversation.messages[-1]["name"], "agent", "Expected agent to respond with greeting")
        
        workflow.run("Which is the capital of France?")
        self.assertEqual(len(workflow.conversation.messages), 5, "Expected 5 messages in the conversation")
        self.assertEqual(workflow.conversation.messages[-1]["name"], "agent", "Expected agent to respond")
        self.assertIn("Paris", workflow.conversation.messages[-1]["content"], "Expected agent to respond 'Paris'")
        
    def test_user_interactive(self):
        agent1 = Agent(id="agent", llm=self.llm, description="Call this agent to answer questions by the user", system_message = """You are an AI assistant
        Your task is to help the user with their questions.
        Always respond with the best answer you can generate.
        If you don't know the answer, respond with "I don't know".
        Always be polite and helpful.
        """)
        
        def fake_input(prompt):
            return "Which is the capital of France?"

        user = User(id="user", mode="interactive", interaction_function=fake_input)
        
        # Must force the stop callback to be triggered by the number of messages, otherwise the test will hang
        flow = Team(id="team", description="", members=[agent1, user], llm=self.llm, stop_callback=lambda msgs: len(msgs) == 5)
        workflow = Workflow(askable=flow)
        
        workflow.restart()
        workflow.run("Hi! Can you help me with capital cities?")
        
        self.assertEqual(len(workflow.conversation.messages), 5, "Expected 5 messages")
        self.assertEqual(workflow.conversation.messages[-1]["name"], "agent", "Expected agent to respond")
        self.assertIn("Paris", workflow.conversation.messages[-1]["content"], "Expected agent to respond 'Paris'")


if __name__ == '__main__':
    unittest.main()