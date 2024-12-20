import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.user import User
from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.sequence import Sequence
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv
load_dotenv(override=True)

class TestSequence(unittest.TestCase):

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

    def test_sequence(self):
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
        
        workflow.run("Which channel is this conversation on?")
        
        self.assertEqual(len(workflow.conversation.messages), 4, "Expected 3 messages in the conversation")
        
        self.assertEqual("first", workflow.conversation.messages[2]['name'], "Expected first agent to be the first to respond")
        
        self.assertEqual("second", workflow.conversation.messages[3]['name'], "Expected second agent to be the second to respond")
        
    def test_sequence_streaming(self):
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
        
        for mark, content in workflow.run_stream("Which channel is this conversation on?"):
            if mark == "end" and content == flow.id:
                break

    def test_user_sequence(self):
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
        flow = Sequence(id="team", description="", steps=[agent1, user], llm=self.llm)
        workflow = Workflow(askable=flow)
        
        workflow.restart()
        workflow.run("Hi! Can you help me with capital cities?")


if __name__ == '__main__':
    unittest.main()