import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vanilla_aiagents.conversation import (
    Conversation,
    NoopUpdateStrategy,
    ReplaceLastMessageUpdateStrategy,
    AppendMessagesUpdateStrategy,
)
from vanilla_aiagents.llm import AzureOpenAILLM
from vanilla_aiagents.agent import Agent

from dotenv import load_dotenv

load_dotenv(override=True)


class TestReadingStrategy(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM(
            {
                "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_KEY"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
            }
        )

        logging.basicConfig(level=logging.INFO)
        logging.getLogger("vanilla_aiagents.conversation").setLevel(logging.DEBUG)

    def test_append(self):
        agent = Agent(
            id="test-agent",
            description="Test Agent",
            system_message="Simply say 'hello'",
            llm=self.llm,
            update_strategy=AppendMessagesUpdateStrategy(),
        )

        conversation = Conversation(messages=[], variables={})
        agent.ask(conversation)

        self.assertEqual(
            len(conversation.messages), 1, "Expected 1 message in the conversation"
        )

    def test_replace(self):
        agent = Agent(
            id="test-agent",
            description="Test Agent",
            system_message="Always respond 'I am sorry' to any ask",
            llm=self.llm,
            update_strategy=ReplaceLastMessageUpdateStrategy(),
        )

        conversation = Conversation(messages=[], variables={})
        conversation.messages.append(
            {"role": "assistant", "content": "Can I order a pizza?"}
        )
        agent.ask(conversation)

        self.assertEqual(
            len(conversation.messages), 1, "Expected 1 message in the conversation"
        )
        self.assertNotIn(
            "pizza",
            conversation.messages[0]["content"],
            "Expected message to be replaced",
        )

    def test_noop(self):
        agent = Agent(
            id="test-agent",
            description="Test Agent",
            system_message="Simply say 'hello'",
            llm=self.llm,
            update_strategy=NoopUpdateStrategy(),
        )

        conversation = Conversation(messages=[], variables={})
        conversation.messages.append(
            {"role": "assistant", "content": "This will not be replaced"}
        )
        agent.ask(conversation)

        self.assertEqual(
            len(conversation.messages), 1, "Expected 1 message in the conversation"
        )
        self.assertNotIn(
            "hello",
            conversation.messages[0]["content"],
            "Expected message NOT to be replaced",
        )


if __name__ == "__main__":
    unittest.main()
