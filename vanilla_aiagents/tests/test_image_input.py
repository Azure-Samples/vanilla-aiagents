import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.workflow import Workflow, WorkflowInput
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.sequence import Sequence
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv
load_dotenv(override=True)

class TestContext(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })
        
        # Set logging to debug for Agent, User, and Workflow
        logging.basicConfig(level=logging.INFO)

    def test_image_input(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        agent = Agent(id="first", llm=self.llm, description="First agent", system_message = """You are part of an AI process
        Your task is to understand the user provided image to understand what problem they are facing.
        Be sure to recognize the objects in the image and provide a helpful response.
        """)
        
        data = WorkflowInput(text="")
        data.add_image_file(os.path.join(os.path.dirname(__file__), "iphone_sim_error.jpg"))
        workflow = Workflow(askable=agent)
        workflow.restart()
        workflow.run(data)
        
        self.assertIn("iPhone", workflow.conversation.messages[-1]["content"], "Expected agent to recognize iPhone in the image")
        self.assertIn("SIM", workflow.conversation.messages[-1]["content"], "Expected agent to recognize sim in the image")
        
    def test_image_input_bytes(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        agent = Agent(id="first", llm=self.llm, description="First agent", system_message = """You are part of an AI process
        Your task is to understand the user provided image to understand what problem they are facing.
        Be sure to recognize the objects in the image and provide a helpful response.
        """)
        
        data = WorkflowInput(text="")
        with open(os.path.join(os.path.dirname(__file__), "iphone_sim_error.jpg"), "rb") as f:
            data.add_image_bytes(f.read())
        workflow = Workflow(askable=agent)
        workflow.restart()
        workflow.run(data)
        
        self.assertIn("iPhone", workflow.conversation.messages[-1]["content"], "Expected agent to recognize iPhone in the image")
        self.assertIn("SIM", workflow.conversation.messages[-1]["content"], "Expected agent to recognize sim in the image")


if __name__ == '__main__':
    unittest.main()