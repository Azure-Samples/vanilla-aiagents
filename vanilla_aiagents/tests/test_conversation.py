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

class TestConversation(unittest.TestCase):

    def setUp(self):
        pass
        # self.llm = AzureOpenAILLM({
        #     "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
        #     "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        #     "api_key": os.getenv("AZURE_OPENAI_KEY"),
        #     "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        # })

    def test_from_dict(self):
        source = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help you today?"}
            ],
            "variables": {
                "user": "John Doe",
                "age": 25
            },
            "metrics": {
                "total_tokens": 100,
                "prompt_tokens": 50,
                "completion_tokens": 50
            },
            "log": [
                ("info", "conversation", "start"),
                ("info", "conversation", "end")
            ]
        }
        conversation = Conversation.from_dict(source)
        
        self.assertEqual(conversation.messages, source["messages"])
        self.assertEqual(conversation.variables, source["variables"])
        self.assertEqual(conversation.metrics.total_tokens, source["metrics"]["total_tokens"])
        self.assertEqual(conversation.metrics.prompt_tokens, source["metrics"]["prompt_tokens"])
        self.assertEqual(conversation.metrics.completion_tokens, source["metrics"]["completion_tokens"])
        self.assertEqual(conversation.log, source["log"])        
        

if __name__ == '__main__':
    unittest.main()