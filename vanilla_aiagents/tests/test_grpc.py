import unittest
import os, logging, sys

import grpc
from grpc_reflection.v1alpha import reflection
from grpc_reflection.v1alpha.reflection_pb2 import ServerReflectionRequest
from grpc_reflection.v1alpha.reflection_pb2_grpc import ServerReflectionStub

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.conversation import Conversation
from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.llm import AzureOpenAILLM
from vanilla_aiagents.remote.remote import RemoteAskable
from vanilla_aiagents.remote.grpc import GRPCHost, GRPCConnection

from dotenv import load_dotenv
load_dotenv(override=True)

class TestGRPC(unittest.TestCase):

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
        logging.getLogger("vanilla_aiagents.remote").setLevel(logging.DEBUG)
        
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
        
    def test_grpc(self):
        
        host = GRPCHost(askables=[self.agent1, self.agent2], host="localhost", port=5002)
        self.assertCountEqual([self.agent1, self.agent2], host.askables, "Expected askables to be the same")
        
        host.start()
        
        connection = GRPCConnection(url="localhost:5002")
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
    
    def test_grpc_streaming(self):
        
        host = GRPCHost(askables=[self.agent1, self.agent2], host="localhost", port=5003)
        self.assertCountEqual([self.agent1, self.agent2], host.askables, "Expected askables to be the same")
        
        host.start()
        
        connection = GRPCConnection(url="localhost:5003")
        remote = RemoteAskable(id="agent1", connection=connection)
        workflow = Workflow(askable=remote, conversation=Conversation())
        
        self.assertEqual(self.agent1.id, workflow.askable.id, "Expected askable ID to be agent1")
        self.assertEqual(self.agent1.description, workflow.askable.description, "Expected askable description to be the same as agent1")
        
        workflow.restart()
        result = None
        for mark, content in workflow.run_stream("Which is the capital of France?"):
            if mark == "response":
                result = content[0]
                break
            if mark == "error":
                break
            
        self.assertIn("Paris", result["content"],"Expected agent to respond 'Paris'")
        
        host.stop()
        
    def test_grpc_reflection(self):
        host = GRPCHost(askables=[self.agent1, self.agent2], host="localhost", port=5004)
        host.start()

        # Create a gRPC channel and reflection stub
        channel = grpc.insecure_channel("localhost:5004")
        stub = ServerReflectionStub(channel)

        # Request the list of services
        request = ServerReflectionRequest(list_services="")
        response = stub.ServerReflectionInfo(iter([request]))

        services = []
        for resp in response:
            services.extend(resp.list_services_response.service)

        # Check if the RemoteService is in the list of services
        service_names = [service.name for service in services]
        self.assertIn("remote.grpc.RemoteService", service_names, "Expected RemoteService to be in the list of services")

        host.stop()


if __name__ == '__main__':
    unittest.main()