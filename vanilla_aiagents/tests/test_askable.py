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

class TestAskable(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })
        self.askable = Agent(id="foo", llm=self.llm, description="Call this agent to answer questions by the user", system_message = """You are an AI assistant""")

    def test_basics(self):
        
        self.askable.id = "bar"
        self.assertEqual(self.askable.id, "bar", "Expected id to be 'bar'")
        
        self.askable.description = "Call this agent to help the user"
        self.assertEqual(self.askable.description, "Call this agent to help the user", "Expected description to be 'Call this agent to help the user'")

    # def test_ask(self):
    #     conversation = Conversation()
    #     conversation.messages = [{"role": "user", "content": "Hello"}]
    #     result = self.askable.ask(conversation)

if __name__ == '__main__':
    unittest.main()