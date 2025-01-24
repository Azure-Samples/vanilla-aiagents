from abc import ABC, abstractmethod
from queue import SimpleQueue
from pydantic import BaseModel

from .llm import LLM
import logging

logger = logging.getLogger(__name__)


# a ConversationMetrics class with totalTokens, promptTokens and completionTokens
class ConversationMetrics(BaseModel):
    """A class to store conversation metrics."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


class Conversation:
    messages: list[dict]
    variables: dict[str, str]
    log: list
    metrics: ConversationMetrics
    """A class to represent a conversation.

    This is only stateful object in the system, and is used to store the conversation
    state, including messages, variables, and metrics.
    """

    def __init__(
        self,
        messages: list[dict] = [],
        variables: dict[str, str] = {},
        metrics=ConversationMetrics(
            total_tokens=0, prompt_tokens=0, completion_tokens=0
        ),
        log=[],
    ):
        """Initialize the Conversation object. All arguments are optional.

        Args:
            messages (list[dict]): The list of messages in the conversation.
            variables (dict[str, str]): The variables in the conversation.
            metrics (ConversationMetrics): The metrics of the conversation.
            log (list): The log of the conversation.
        """
        self.messages = messages
        self.variables = variables
        self.log = log
        self.metrics = metrics
        self.stream_queue = SimpleQueue()

    def stream(self):
        """Stream conversation updates, like LLM delta updates, to the consumer.

        NOTE this is an INFINITE generator function, and must be kept so. Consumers
        should break the loop themselves, typically using a stack count logic
        """
        while True:
            mark, content = self.stream_queue.get()
            yield [mark, content]

    def update(self, delta):
        """Update the conversation signalling a delta."""
        self.stream_queue.put_nowait(delta)

    def to_dict(self):
        """Convert the conversation to a raw dictionary."""
        return {
            "messages": self.messages,
            "variables": self.variables,
            "metrics": self.metrics.model_dump(),
        }

    def fork(self):
        """Fork the conversation into a new conversation object."""
        return Conversation(
            messages=self.messages.copy(), variables=self.variables.copy()
        )

    @classmethod
    def from_dict(cls, data: dict):
        """Create a conversation object from a raw dictionary."""
        return cls(
            messages=data.get("messages", []),
            variables=data.get("variables", {}),
            log=data.get("log", []),
            metrics=ConversationMetrics(**data.get("metrics", {})),
        )


class ConversationReadingStrategy(ABC):
    """Base class for conversation reading strategies."""

    @abstractmethod
    def get_messages(self, conversation: Conversation) -> list[dict]:
        pass

    def exclude_system_messages(self, messages: list[dict]) -> list[dict]:
        return [message for message in messages if message["role"] != "system"]


class LastNMessagesStrategy(ConversationReadingStrategy):
    """A conversation reading strategy that reads the last N messages from the conversation."""

    def __init__(self, n: int):
        """
        Initialize the LastNMessagesStrategy.

        Args:
            n (int): The number of messages to read.
        """
        self.n = n

    def get_messages(self, conversation: Conversation) -> list[dict]:
        return self.exclude_system_messages(conversation.messages)[-self.n :]


class AllMessagesStrategy(ConversationReadingStrategy):
    """A conversation reading strategy that reads all messages from the conversation."""

    def get_messages(self, conversation: Conversation) -> list[dict]:
        return self.exclude_system_messages(conversation.messages)


class TopKLastNMessagesStrategy(ConversationReadingStrategy):
    """A conversation reading strategy that reads the top K and last N messages from the conversation."""

    def __init__(self, k: int, n: int):
        """
        Initialize the TopKLastNMessagesStrategy.

        Args:
            k (int): The number of top messages to read.
            n (int): The number of last messages to read.
        """
        self.k = k
        self.n = n

    def get_messages(self, conversation: Conversation) -> list[dict]:
        list = self.exclude_system_messages(conversation.messages)
        return list[: self.k] + list[-self.n :]


class SummarizeMessagesStrategy(ConversationReadingStrategy):
    """A conversation reading strategy that summarizes the conversation messages into a single message."""

    def __init__(self, llm: LLM, system_prompt: str):
        """
        Initialize the SummarizeMessagesStrategy.

        Args:
            llm (LLM): The language model to use for summarization.
            system_prompt (str): The system prompt to use for summarization.
        """
        super().__init__()
        self.llm = llm
        self.system_prompt = system_prompt

    def get_messages(self, conversation: Conversation) -> list[dict]:
        # Extract the conversation text from the messages
        local_messages = []
        local_messages += self.exclude_system_messages(conversation.messages)
        local_messages.append({"role": "user", "content": self.system_prompt})

        # Summarize the conversation text
        response, usage = self.llm.ask(messages=local_messages)
        response_message = response.model_dump()
        summarized_text = response_message["content"]

        return [{"role": "assistant", "name": "summarizer", "content": summarized_text}]


class PipelineConversationReadingStrategy(ConversationReadingStrategy):
    """A conversation reading strategy that reads the conversation messages through a pipeline of strategies."""

    def __init__(self, strategies: list[ConversationReadingStrategy]):
        """
        Initialize the PipelineConversationReadingStrategy.

        Args:
            strategies (list[ConversationReadingStrategy]): The list of strategies to use in the pipeline.
        """
        self.strategies = strategies

    def get_messages(self, conversation: Conversation) -> list[dict]:
        messages = conversation.messages
        for strategy in self.strategies:
            messages = strategy.get_messages(Conversation(messages=messages))
        return messages


class ConversationUpdateStrategy(ABC):
    """Base class for conversation update strategies."""

    @abstractmethod
    def update(self, conversation: Conversation, delta: any):
        pass


class AppendMessagesUpdateStrategy(ConversationUpdateStrategy):
    """An update strategy that appends messages to the conversation."""

    def update(self, conversation: Conversation, delta: any):
        if isinstance(delta, list):
            conversation.messages += delta
        else:
            conversation.messages += [delta]


class ReplaceLastMessageUpdateStrategy(ConversationUpdateStrategy):
    """An update strategy that replaces the last message in the conversation."""

    def update(self, conversation: Conversation, delta: any):
        conversation.messages[-1] = delta


class NoopUpdateStrategy(ConversationUpdateStrategy):
    """No operation update strategy, does not update the conversation.

    Useful for agents that do not need to update messages, but only invoke functions or
    set variables.
    """

    def update(self, conversation: Conversation, delta: any):
        pass
