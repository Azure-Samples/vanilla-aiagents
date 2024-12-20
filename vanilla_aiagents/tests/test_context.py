import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.workflow import Workflow
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
        # logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        # logging.getLogger("vanilla_aiagents.user").setLevel(logging.DEBUG)
        # logging.getLogger("vanilla_aiagents.workflow").setLevel(logging.DEBUG)

    def test_context(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(id="first", llm=self.llm, description="First agent", system_message = """You are part of an AI process
        Your task is to set a context for the next agent to continue the conversation.

        DO set context variable "CHANNEL" to "voice" and "LANGUAGE" to "en"

        DO respond only "Context set" when you are done.
        """)

        # Second agent might have its system message extended automatically with the context from the ongoing conversation
        second = Agent(id="second", llm=self.llm, description="Second agent", system_message = """You are part of an AI process
        Your task is to continue the conversation based on the context set by the previous agent.
        When asked, you can use variable provide in CONTEXT to generate the response.

        --- CONTEXT ---
        __context__
        """)
        
        flow = Sequence(id="flow", description="", steps=[first, second], llm=self.llm)
        workflow = Workflow(askable=flow)
        workflow.restart()
        
        workflow.run("Which channel is this conversation on?")
        
        self.assertEqual(len(workflow.conversation.messages), 4, "Expected 3 messages in the conversation")
        
        self.assertIn("Context set", workflow.conversation.messages[2]["content"], "Expected context to be set")
        self.assertIn("voice", workflow.conversation.messages[3]["content"], "Expected second agent to recognize context variable CHANNEL")


if __name__ == '__main__':
    unittest.main()