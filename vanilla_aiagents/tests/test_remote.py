import unittest
import os, logging, sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.conversation import Conversation
from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.user import User
from vanilla_aiagents.team import Team
from vanilla_aiagents.llm import AzureOpenAILLM
from vanilla_aiagents.remote.remote import RESTHost, RemoteAskable, RESTConnection
from vanilla_aiagents.remote.grpc import GRPCHost, GRPCConnection

from dotenv import load_dotenv
load_dotenv(override=True)

class TestRemote(unittest.TestCase):

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
        logging.getLogger("vanilla_aiagents.remote.remote").setLevel(logging.DEBUG)
        
        self.agent1 = Agent(id="agent1", llm=self.llm, description="Call this agent for general purpose questions", system_message = """You are an AI assistant
        Your task is to help the user with their questions.
        Always respond with the best answer you can generate.
        If you don't know the answer, respond with "I don't know".
        Always be polite and helpful.
        """)
        
        self.agent2 = Agent(id="agent2", llm=self.llm, description="Call this agent for general purpose questions", system_message = """You are an AI assistant
        Your task is to help the user with their questions.
        Always respond with the best answer you can generate.
        If you don't know the answer, respond with "I don't know".
        Always be polite and helpful.
        """)

    def test_rest(self):
        
        host = RESTHost(askables=[self.agent1, self.agent2], host="127.0.0.1", port=5000)
        self.assertCountEqual([self.agent1, self.agent2], host.askables, "Expected askables to be the same")
        
        host.start()
        
        connection = RESTConnection(url="http://localhost:5000")
        remote = RemoteAskable(id="agent1", connection=connection)
        workflow = Workflow(askable=remote, conversation=Conversation())
        
        self.assertEqual(self.agent1.id, workflow.askable.id, "Expected askable ID to be agent1")
        self.assertEqual(self.agent1.description, workflow.askable.description, "Expected askable description to be the same as agent1")
        
        workflow.restart()
        workflow.run("Which is the capital of France?")
        
        host.stop()
        
        # Note name in RemoteAskable is the one set in the response
        self.assertEqual(workflow.conversation.messages[-1]["name"], "agent1", "Expected agent to respond with greeting")
        self.assertEqual(workflow.conversation.messages[-1]["name"], "agent1", "Expected agent to respond")
        self.assertIn("Paris", workflow.conversation.messages[-1]["content"], "Expected agent to respond 'Paris'")
        
    def test_rest_streaming(self):
        
        host = RESTHost(askables=[self.agent1], host="127.0.0.1", port=5001)
        
        host.start()
        
        connection = RESTConnection(url="http://localhost:5001")
        remote = RemoteAskable(id="agent1", connection=connection)
        workflow = Workflow(askable=remote, conversation=Conversation())
        
        result = None
        for mark, content in workflow.run_stream("Which is the capital of France?"):
            if mark == "response":
                result = content[0]
                break
            if mark == "error":
                break
            
        self.assertIn("Paris", result["content"],"Expected agent to respond 'Paris'")
        
        host.stop()


if __name__ == '__main__':
    unittest.main()