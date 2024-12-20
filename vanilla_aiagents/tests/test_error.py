import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.conversation import Conversation
from vanilla_aiagents.askable import Askable
from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.sequence import Sequence
from vanilla_aiagents.llm import AzureOpenAILLM, ErrorTestingLLM
from vanilla_aiagents.planned_team import PlannedTeam
from vanilla_aiagents.team import Team

from dotenv import load_dotenv
load_dotenv(override=True)

class TestLLM(unittest.TestCase):

    def setUp(self):
        
        self.llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })
        self.fake_llm = ErrorTestingLLM({})
        
        # Set logging to debug for Agent, User, and Workflow
        logging.basicConfig(level=logging.INFO)
        # logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        # logging.getLogger("vanilla_aiagents.user").setLevel(logging.DEBUG)
        # logging.getLogger("vanilla_aiagents.workflow").setLevel(logging.DEBUG)    
        
    def test_sequence_error(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(id="first", llm=self.fake_llm, description="First agent", system_message = """You are part of an AI process
        Your task is to set a context for the next agent to continue the conversation.

        DO set context variable "CHANNEL" to "voice" and "LANGUAGE" to "en"

        DO respond only "Context set" when you are done.
        """)

        # Second agent might have its system message extended automatically with the context from the ongoing conversation
        second = Agent(id="second", llm=self.fake_llm, description="Second agent", system_message = """You are part of an AI process
        Your task is to continue the conversation based on the context set by the previous agent.
        When asked, you can use variable provide in CONTEXT to generate the response.

        --- CONTEXT ---
        __context__
        """)
        
        flow = Sequence(id="flow", description="", steps=[first, second], llm=self.llm)
        workflow = Workflow(askable=flow)
        
        workflow.run("Which channel is this conversation on?")
        
        result = workflow.run("Which channel is this conversation on?")
        
        self.assertEqual(result, "agent-error", "Expected error result from the workflow")
        
    def test_team_error(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(id="first", llm=self.fake_llm, description="First agent", system_message = """You are part of an AI process
        Your task is to set a context for the next agent to continue the conversation.

        DO set context variable "CHANNEL" to "voice" and "LANGUAGE" to "en"

        DO respond only "Context set" when you are done.
        """)

        # Second agent might have its system message extended automatically with the context from the ongoing conversation
        second = Agent(id="second", llm=self.fake_llm, description="Second agent", system_message = """You are part of an AI process
        Your task is to continue the conversation based on the context set by the previous agent.
        When asked, you can use variable provide in CONTEXT to generate the response.

        --- CONTEXT ---
        __context__
        """)
        
        flow = Team(id="flow", description="", members=[first, second], llm=self.llm)
        workflow = Workflow(askable=flow)
        
        result = workflow.run("Which channel is this conversation on?")
        
        self.assertEqual(result, "agent-error", "Expected error result from the workflow")
        
    def test_planned_team_error(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(id="first", llm=self.fake_llm, description="First agent", system_message = """You are part of an AI process
        Your task is to set a context for the next agent to continue the conversation.

        DO set context variable "CHANNEL" to "voice" and "LANGUAGE" to "en"

        DO respond only "Context set" when you are done.
        """)

        # Second agent might have its system message extended automatically with the context from the ongoing conversation
        second = Agent(id="second", llm=self.fake_llm, description="Second agent", system_message = """You are part of an AI process
        Your task is to continue the conversation based on the context set by the previous agent.
        When asked, you can use variable provide in CONTEXT to generate the response.

        --- CONTEXT ---
        __context__
        """)
        
        flow = PlannedTeam(id="flow", description="", members=[first, second], llm=self.llm)
        workflow = Workflow(askable=flow)
        
        result = workflow.run("Which channel is this conversation on?")
        
        self.assertEqual(result, "agent-error", "Expected error result from the workflow")
        
    def test_agent_error(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(id="first", llm=self.fake_llm, description="First agent", system_message = """You are an AI assistant""")
        
        workflow = Workflow(askable=first)
        
        result = workflow.run("Which channel is this conversation on?")
        
        self.assertEqual(result, "error", "Expected error result from the workflow")
        
    def test_workflow_error(self):
        class ErrorAgent(Askable):
            def __init__(self, id, description):
                super().__init__(id, description)
                
            def ask(self, conversation: Conversation, stream = False) -> str:
                raise Exception("Fake Error")
            
        workflow = Workflow(askable=ErrorAgent(id="error", description="Fake Error Agent"))
        
        result = None
        for mark, content in workflow.run_stream("Which channel is this conversation on?"):
            if mark == "result":
                result = content
                break
        
        self.assertEqual(result, "error", "Expected error result from the workflow")
        


if __name__ == '__main__':
    unittest.main()