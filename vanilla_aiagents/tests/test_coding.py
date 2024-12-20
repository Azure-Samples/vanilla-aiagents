from typing import Annotated
import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.azure_coding_agent import AzureCodingAgent
from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.user import User
from vanilla_aiagents.team import Team
from vanilla_aiagents.llm import AzureOpenAILLM
from vanilla_aiagents.coding_agent import LocalCodingAgent

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
        logging.getLogger("vanilla_aiagents.coding_agent").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.llm").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.team").setLevel(logging.DEBUG)
        
        
        localCodingAgent = LocalCodingAgent(id="agent1", description="Agent 1", llm=self.llm)
        azureCodingAgent = AzureCodingAgent(id="agent2", description="Agent 2", llm=self.llm)

        flow = Team(id="team", description="An agent capable of writing and executing code", members=[localCodingAgent], llm=self.llm, stop_callback=lambda msgs: len(msgs) > 2)
        self.local_workflow = Workflow(askable=flow)
        self.azure_workflow = Workflow(askable=azureCodingAgent)

    # Not working yet on GH actions
    # def test_basic_math(self):
    #     self.local_workflow.restart()
    #     self.local_workflow.run("Which is the square root of 256?")
        
    #     self.assertIn("16", self.local_workflow.conversation.messages[-1]["content"], "Expected agent to respond 16")
        
    def test_yfinance(self):
        self.local_workflow.restart()
        self.local_workflow.run("What is latest quote for Apple Inc. stock? Generate code to get the quote using yfinance and return only the latest quote (include $)")
        
        self.assertIn("$", self.local_workflow.conversation.messages[-1]["content"], "Expected agent to respond with a quote")
    
    def test_azure_basic_math(self):
        self.azure_workflow.restart()
        self.azure_workflow.run("Which is the square root of 256?")
        
        self.assertIn("16", self.azure_workflow.conversation.messages[-1]["content"], "Expected agent to respond 16")
        
    def test_azure_yfinance(self):
        self.azure_workflow.restart()
        self.azure_workflow.run("What is latest quote for Apple Inc. stock? Generate code to get the quote using yfinance and return only the latest quote (include $)")
        
        self.assertIn("$", self.azure_workflow.conversation.messages[-1]["content"], "Expected agent to respond with a quote")


if __name__ == '__main__':
    unittest.main()