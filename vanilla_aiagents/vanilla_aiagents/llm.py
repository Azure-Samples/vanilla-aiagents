from collections import defaultdict
from typing import Generator, NamedTuple, Optional
from openai import NOT_GIVEN, AzureOpenAI, Stream
from openai.types.chat import ChatCompletionChunk
from abc import ABC, abstractmethod
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

import json
import logging

logger = logging.getLogger(__name__)


class LLMConstraints(NamedTuple):
    system_message: bool = False
    structured_output: bool = True
    temperature: Optional[float] = None


class LLM(ABC):
    """Abstract class for the Language Model clients."""

    def __init__(self, config: dict, constraints: Optional[LLMConstraints] = LLMConstraints()):
        """
        Initialize the LLM client.

        Args:
            config (dict): The configuration for the client.
        """
        self.config = config
        self.constraints = constraints

    @abstractmethod
    def ask(
        self,
        messages: list,
        tools: list = None,
        tools_function: dict[str, callable] = None,
        temperature: float = 0.7,
        response_format=None,
    ) -> tuple[dict, dict]:
        pass

    @abstractmethod
    def ask_stream(
        self,
        messages: list,
        tools: list = None,
        tools_function: dict[str, callable] = None,
        temperature: float = 0.7,
    ) -> Generator[tuple[str, any], None, tuple[dict, any]]:
        pass
    
    def _check_system_messages(self, messages: list) -> list:
        """Ensures that system messages are not sent to the LLM when the constraints are set.

        Args:
            messages (list): The list of messages to convert.

        Returns:
            list: The converted list of messages.
        """
        if not self.constraints.system_message:
            copy = messages.copy()
            for message in copy:
                if message["role"] == "system":
                    message["role"] = "assistant"
            return copy
        
        return messages


class ErrorTestingLLM(LLM):
    """LLM that raises an error when asked.

    Used for testing error handling.
    """

    def __init__(self, config: dict, constraints: Optional[LLMConstraints] = LLMConstraints()):
        """
        Initialize the ErrorTestingLLM client.

        Args:
            config (dict): The configuration for the client.
        """
        super().__init__(config, constraints=constraints)

    def ask(
        self,
        messages: list,
        tools: list = None,
        tools_function: dict[str, callable] = None,
        temperature: float = 0.7,
        response_format=None,
    ):
        raise Exception("Fake error")

    def ask_stream(
        self,
        messages: list,
        tools: list = None,
        tools_function: dict[str, callable] = None,
        temperature: float = 0.7,
    ):
        yield ["start", ""]
        yield ["error", "Fake error"]
        yield ["end", ""]
        return None, None


class AzureOpenAILLM(LLM):
    """LLM using Azure OpenAI API.

    Args:
    - config: dict with the following
        - azure_deployment: str, Azure deployment name
        - azure_endpoint: str, Azure endpoint
        - api_key: str, Azure API key. Leave empty if using Azure AD token provider
        - api_version: str, API version
    """

    def __init__(self, config: dict, constraints: Optional[LLMConstraints] = LLMConstraints()):
        """Initialize the AzureOpenAILLM client.

        Args:
            config (dict): The configuration for the client.
        """
        super().__init__(config, constraints=constraints)

        api_key = self.config["api_key"]
        token_provider = (
            get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            if api_key is None or api_key == ""
            else None
        )
        self.client = AzureOpenAI(
            azure_deployment=self.config["azure_deployment"],
            api_key=self.config["api_key"],
            azure_endpoint=self.config["azure_endpoint"],
            api_version=self.config["api_version"],
            azure_ad_token_provider=token_provider,
        )
        logger.debug(
            "LLM initialized with AzureOpenAI client with %s",
            "api_key" if api_key else "token provider",
        )

    def ask(
        self,
        messages: list,
        tools: list = None,
        tools_function: dict[str, callable] = None,
        temperature: float = 0.7,
        response_format=NOT_GIVEN,
    ):
        """Ask the LLM to generate a completion given the messages.

        Args:
            messages (list): The list of messages to send to the LLM.
            tools (list): The list of tools to use in the LLM.
            tools_function (dict): The dictionary of tool functions to use in the LLM.
            temperature (float): The temperature to use in the LLM.
            response_format: The response format to use in the LLM (Structured Output)

        Returns:
            tuple: The response message and the usage metrics.
        """
        # logger.debug("Received messages: %s", messages)
        
        temperature = self.constraints.temperature if self.constraints.temperature else temperature
        messages = self._check_system_messages(messages)

        if not self.constraints.structured_output or response_format is NOT_GIVEN:
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.config["azure_deployment"],
                tools=tools if tools and len(tools) > 0 else NOT_GIVEN,
                temperature=temperature,
                tool_choice="auto" if tools else NOT_GIVEN,
            )
        else:
            response = self.client.beta.chat.completions.parse(
                messages=messages,
                model=self.config["azure_deployment"],
                tools=tools if tools and len(tools) > 0 else NOT_GIVEN,
                temperature=temperature,
                tool_choice="auto" if tools else NOT_GIVEN,
                response_format=response_format,
            )

        response_message = response.choices[0].message
        logger.debug("Response message: %s", response_message)

        # Handle function calls (if any)
        # Must iterate until there are no more tool calls
        while response_message.tool_calls:
            logger.debug("Tool calls detected: %s", response_message.tool_calls)
            messages.append(response.choices[0].message)
            for tool_call in response_message.tool_calls:
                function_args = json.loads(tool_call.function.arguments)
                logger.debug("Function arguments: %s", function_args)

                function_result = tools_function[tool_call.function.name](
                    **function_args
                )
                logger.debug("Function result: %s", function_result)

                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": function_result,
                    }
                )

            # Second API call: Get the next response from the model given the func call result
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.config["azure_deployment"],
                tools=tools,
                temperature=temperature,
                tool_choice="auto" if tools else None,
            )
            response_message = response.choices[0].message

        logger.debug("Final response message: %s", response_message)

        # NOTE purposely not returning all the intermediate messages, only the final response

        return response_message, {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    def ask_stream(
        self,
        messages: list,
        tools: list = None,
        tools_function: dict[str, callable] = None,
        temperature: float = 0.7,
    ):
        """Ask the LLM to generate a completion given the messages and stream the updates.

        Args:
            messages (list): The list of messages to send to the LLM.
            tools (list): The list of tools to use in the LLM.
            tools_function (dict): The dictionary of tool functions to use in the LLM.
            temperature (float): The temperature to use in the LLM.

        Yields:
            tuple: The mark and content of the conversation update.
        """
        # Accumulate messages and usage
        response_message = None
        usage = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
        temperature = self.constraints.temperature if self.constraints.temperature else temperature
        messages = self._check_system_messages(messages)

        yield ["start", ""]
        while True:
            response_message = {
                "content": "",
                "role": "assistant",
                "function_call": None,
                "tool_calls": defaultdict(
                    lambda: {
                        "function": {"arguments": "", "name": ""},
                        "id": "",
                        "type": "",
                    }
                ),
            }

            # Call LLM with stream=True
            completion: Stream[ChatCompletionChunk] = (
                self.client.chat.completions.create(
                    messages=messages,
                    model=self.config["azure_deployment"],
                    tools=tools,
                    temperature=temperature,
                    tool_choice="auto" if tools else None,
                    stream=True,
                    stream_options={"include_usage": True},
                )
            )

            # Yield the intermediate updates
            for chunk in completion:
                if len(chunk.choices) > 0:
                    delta = json.loads(chunk.choices[0].delta.model_dump_json())
                    yield ["delta", delta]
                    delta.pop("role", None)
                    delta.pop("name", None)
                    # Update the accumulated response message
                    merge_chunk(response_message, delta)
                # Also accumulate usage, if any
                if chunk.usage:
                    usage["completion_tokens"] += chunk.usage.completion_tokens
                    usage["prompt_tokens"] += chunk.usage.prompt_tokens
                    usage["total_tokens"] += chunk.usage.total_tokens

            logger.debug("Response message: %s", response_message)

            # Handle function calls (if any)
            if (
                not response_message["tool_calls"]
                or len(response_message["tool_calls"]) == 0
            ):
                break
            else:
                response_message["tool_calls"] = list(
                    response_message.get("tool_calls", {}).values()
                )

            logger.debug("Tool calls detected: %s", response_message["tool_calls"])
            messages.append(response_message)
            for tool_call in response_message["tool_calls"]:
                function_args = json.loads(tool_call["function"]["arguments"])
                logger.debug("Function arguments: %s", function_args)

                function_result = tools_function[tool_call["function"]["name"]](
                    **function_args
                )
                logger.debug("Function result: %s", function_result)
                yield [
                    "function_result",
                    {"name": tool_call["function"]["name"], "result": function_result},
                ]

                messages.append(
                    {
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": tool_call["function"]["name"],
                        "content": function_result,
                    }
                )
            # NOTE: The loop will continue until there are no more tool calls

        # Strip the tool calls from the final response message
        response_message.pop("tool_calls", None)
        response_message.pop("function_call", None)

        logger.debug("Final response message: %s", response_message)

        # Return the final response message and usage
        yield ["response", [response_message, usage]]

        yield ["end", ""]

        return [response_message, usage]


def merge_fields(target, source):
    for key, value in source.items():
        if isinstance(value, str):
            target[key] += value
        elif value is not None and isinstance(value, dict):
            merge_fields(target[key], value)


def merge_chunk(source: dict, delta: dict) -> None:
    delta.pop("role", None)
    merge_fields(source, delta)

    tool_calls = delta.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        index = tool_calls[0].pop("index")
        merge_fields(source["tool_calls"][index], tool_calls[0])
