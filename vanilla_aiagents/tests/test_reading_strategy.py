import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.conversation import AllMessagesStrategy, Conversation, LastNMessagesStrategy, TopKLastNMessagesStrategy, SummarizeMessagesStrategy, PipelineConversationReadingStrategy
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv
load_dotenv(override=True)

class TestReadingStrategy(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })
        
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("vanilla_aiagents.conversation").setLevel(logging.DEBUG)
        
        self.conversation = Conversation(messages=[
            {"role": "system", "content": ""},
            {"role": "assistant","name": "agent", "content": "Hello! How can I help you today?"},
            {"role": "user","name": "user", "content": "Hi! Can you help me with capital cities?"},
            {"role": "assistant","name": "agent", "content": "Sure! Which capital you want to learn about?"},
            {"role": "user","name": "user", "content": "Which is the capital of Italy?"},
            {"role": "assistant","name": "agent", "content": "The capital of Italy is Rome."},
            {"role": "user","name": "user", "content": "And the capital of France?"},
            {"role": "assistant","name": "agent", "content": "The capital of France is Paris."},
            {"role": "user","name": "user", "content": "Thank you!"},
            {"role": "assistant","name": "agent", "content": "You're welcome!"},
        ])

    def test_allmessages(self):
        strategy = AllMessagesStrategy()
        result = strategy.get_messages(self.conversation)
        
        self.assertEqual(len(result), len(self.conversation.messages)-1, "Expected ALL messages in the conversation")
        self.assertNotEqual(result[0]["role"], "system", "Expected system message NOT to be included")
        
    def test_lastnmessages(self):
        strategy = LastNMessagesStrategy(n=3)
        result = strategy.get_messages(self.conversation)
        
        self.assertEqual(len(result), 3, "Expected 3 messages in the conversation") # System message is not included
        self.assertEqual(result[0]["role"], "assistant", "Expected system message NOT to be included")
        self.assertEqual(result[1]["role"], "user", "Expected user message to be included")
        
    def test_topklastnmessages(self):
        strategy = TopKLastNMessagesStrategy(k=2, n=3)
        result = strategy.get_messages(self.conversation)
        
        self.assertEqual(len(result), 5, "Expected 2 messages in the conversation")
        self.assertEqual(result[1]["role"], "user", "Expected user message to be included")
        self.assertEqual(result[0]["role"], "assistant", "Expected assistant message to be included")
        self.assertEqual(result[-2]["role"], "user", "Expected user message to be penultimate")
        self.assertEqual(result[-1]["role"], "assistant", "Expected assistant message to be last")
        
    def test_summarizemessages(self):
        strategy = SummarizeMessagesStrategy(llm=self.llm, system_prompt="Summarize the conversation, highlighting the key points in a bullet list")
        result = strategy.get_messages(self.conversation)
                
        self.assertEqual(len(result), 1, "Expected 1 message in the conversation")
        self.assertEqual(result[0]["role"], "assistant", "Expected assistant message to be included")
        
    def test_pipelineconversationreadingstrategy(self):
        strategy = PipelineConversationReadingStrategy([
            LastNMessagesStrategy(n=4),
            SummarizeMessagesStrategy(llm=self.llm, system_prompt="Summarize the conversation, highlighting the key points in a bullet list")
        ])
        
        result = strategy.get_messages(self.conversation)
        
        self.assertEqual(len(result), 1, "Expected 1 message in the conversation")
        self.assertIn("Paris", result[0]["content"], "Expected Paris to be in the summarized text")
        self.assertNotIn("Rome", result[0]["content"], "Expected Rome NOT to be in the summarized text")
        
if __name__ == '__main__':
    unittest.main()