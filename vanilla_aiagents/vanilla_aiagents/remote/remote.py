from abc import abstractmethod
import contextlib
import gzip
import json
import logging
import queue
import time
from typing import Generator, Protocol

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import threading
import requests
import importlib
import os

from starlette_gzip_request import GZipRequestMiddleware

from ..conversation import (
    AllMessagesStrategy,
    Conversation,
    ConversationMetrics,
    ConversationReadingStrategy,
)
from ..askable import Askable

# Configure logging
logger = logging.getLogger(__name__)


class ConversationRequest(BaseModel):
    """A class to store a conversation request to a remote askable."""

    messages: list[dict]
    variables: dict


class ConversationResponse(BaseModel):
    """A class to store a conversation response from a remote askable."""

    messages: list[dict]
    variables: dict
    metrics: ConversationMetrics


class AskResponse(BaseModel):
    """A class to store an ask response from a remote askable."""

    conversation: ConversationResponse
    result: str


class Connection(Protocol):
    """A common interface for a connection to a remote askable."""

    @abstractmethod
    def send(target_id: str, self, operation: str, payload: any) -> dict:
        """Send a payload to the remote askable."""
        pass

    @abstractmethod
    def stream(target_id: str, self, operation: str, payload: any) -> dict:
        """Send a payload to the remote askable and stream the response."""
        pass


class RESTConnection(Connection):
    """A connection to a remote askable using HTTP REST."""

    def __init__(self, url: str):
        """Initialize the RESTConnection object.

        Args:
            url (str): The URL of the remote askable.
        """
        self.url = url
        logger.debug(f"RESTConnection initialized with URL: {self.url}")

    def send(self, target_id: str, operation: str, payload: any) -> dict:
        """Send a payload to the remote askable.

        Args:
            target_id (str): The ID of the remote askable.
            operation (str): The operation to perform.
            payload (any): The payload to send.

        Returns:
            dict: The response from the remote askable, deserialized from JSON.
        """
        logger.debug(f"Sending payload to {self.url}/{operation}: {payload}")
        headers = {"Content-Encoding": "gzip", "Content-Type": "application/json"}
        compressed_payload = gzip.compress(json.dumps(payload).encode("utf-8"))
        response = requests.post(
            f"{self.url}/{target_id}/{operation}",
            data=compressed_payload,
            headers=headers,
        )
        response.raise_for_status()
        response = response.json()
        logger.debug(f"Received response: {response}")

        return response

    def stream(self, target_id: str, operation: str, payload: any):
        """
        Send a payload to the remote askable and stream the response.

        Args:
            target_id (str): The ID of the remote askable.
            operation (str): The operation to perform.
            payload (any): The payload to send.

        Yields:
            dict: The response from the remote askable, deserialized from JSON.
        """
        logger.debug(f"Streaming payload to {self.url}/{operation}: {payload}")
        headers = {"Content-Encoding": "gzip", "Content-Type": "application/json"}
        compressed_payload = gzip.compress(json.dumps(payload).encode("utf-8"))
        response = requests.post(
            f"{self.url}/{target_id}/{operation}?stream=true",
            data=compressed_payload,
            headers=headers,
            stream=True,
        )
        response.raise_for_status()
        result = None
        for line in response.iter_lines():
            if line:
                logger.debug(f"Received line: {line}")
                mark, content = json.loads(line)
                yield [mark, content]
                if mark == "result":
                    result = content
                    break

        return result


class RemoteAskable(Askable):
    """A remote askable that can be asked remotely using a connection."""

    def __init__(
        self,
        id: str,
        connection: Connection,
        reading_strategy: ConversationReadingStrategy = AllMessagesStrategy(),
    ):
        """Initialize the RemoteAskable object.

        Args:
            id (str): The ID of the RemoteAskable object. Will be used to uniquely identify it.
            connection (Connection): The connection to the remote askable.
            reading_strategy (ConversationReadingStrategy): The reading strategy to use to select the messages to send to the remote askable.
        """
        super().__init__("", "")
        self.connection = connection
        self.id = id
        self.reading_strategy = reading_strategy

        response = self.connection.send(self.id, "describe", {})
        self.description = response["description"]

        logger.debug(
            f"RemoteAskable initialized with ID: {self.id}, Description: {self.description}"
        )

    def ask(self, conversation: Conversation, stream=False):
        """Ask the remote askable to solve the user inquiry.

        Args:
            conversation (Conversation): The conversation to use for the execution
            stream (bool): Whether to stream the conversation updates.
        """
        source_messages = self.reading_strategy.get_messages(conversation)
        payload = {"messages": source_messages, "variables": conversation.variables}
        logger.debug(f"Asking with payload: {payload}")

        result = None
        conv = None
        if not stream:
            response = self.connection.send(self.id, "ask", payload)
        else:
            gen = self.connection.stream(self.id, "ask", payload)
            for mark, content in gen:
                conversation.update([mark, content])
                if mark == "result":
                    response = content

        result = response["result"]
        conv = response["conversation"]

        # Original metrics are not part of the payload, so we need to sum them
        conversation.metrics.completion_tokens += conv["metrics"]["completion_tokens"]
        conversation.metrics.prompt_tokens += conv["metrics"]["prompt_tokens"]
        conversation.metrics.total_tokens += conv["metrics"]["total_tokens"]
        # Update the conversation with the new messages
        conversation.messages += conv["messages"][len(source_messages):]
        # Update the conversation variables
        conversation.variables = conv["variables"]
        logger.debug(f"Updated conversation: {conversation}")

        return result


class AskableHost(Protocol):
    """A common interface for a host that can host askables."""

    @abstractmethod
    def start(self):
        """Start the host."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the host."""
        pass


# Inspired by https://bugfactory.io/articles/starting-and-stopping-uvicorn-in-the-background/
class ThreadedServer(uvicorn.Server):
    """A Uvicorn threaded server that can run in a separate thread and started/stopped programmatically."""

    @contextlib.contextmanager
    def run_in_thread(self) -> Generator:
        """Run the server in a separate thread."""
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        logger.debug("Server thread started")
        while not self.started:
            time.sleep(0.001)
        yield
        logger.debug("Server running in thread")


class RESTHost(AskableHost):
    """A host that can host askables using a REST API."""

    def __init__(
        self,
        askables: list[Askable],
        host: str,
        port: int,
        config: uvicorn.Config = None,
    ):
        """Initialize the RESTHost object.

        Args:
            askables (list[Askable]): The askables to host.
            host (str): The host to bind the server to.
            port (int): The port to bind the server to.
            config (uvicorn.Config): The configuration to use for the server.
        """
        self.askables = askables
        self.askables_dict = {askable.id: askable for askable in askables}
        self._build_app()
        self.config = config or uvicorn.Config(app=self.app, host=host, port=port)
        logger.debug(
            f"RESTHost initialized with host: {self.config.host}, port: {self.config.port}"
        )

    def start(self):
        """Start the host."""
        # Start the server
        self.server = ThreadedServer(config=self.config)
        with self.server.run_in_thread():
            logger.info(
                f"Askable server running at http://{self.config.host}:{self.config.port}"
            )
            # Log a message with all available askables
            logger.info(
                f"Available askables: {', '.join([askable.id for askable in self.askables])}"
            )

    def stop(self):
        """Stop the host."""
        logger.debug("Stopping server")
        self.server.should_exit = True
        self.server.thread.join()
        logger.debug("Server stopped")

    def _build_app(self):
        self.app = FastAPI()
        # Enable GZip compression for response
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        self.app.add_middleware(GZipRequestMiddleware)

        @self.app.post("/{id}/describe")
        async def describe(id: str):
            if id in self.askables_dict:
                askable = self.askables_dict[id]
                return {"id": askable.id, "description": askable.description}
            else:
                # Return 404 if the askable is not found
                return {"detail": "Askable not found"}, 404

        @self.app.post("/{id}/ask")
        async def ask(id: str, request: ConversationRequest, stream: bool = False):
            logger.debug(f"Received ask request: {request} for askable {id}")
            conv = Conversation(request.messages, request.variables)

            if id in self.askables_dict:
                askable = self.askables_dict[id]

                if stream:
                    result_queue = queue.SimpleQueue()

                    def ask_in_thread():
                        res = None
                        try:
                            res = askable.ask(conv, True)
                        except Exception as e:
                            logger.error(
                                "Error during askable.ask: %s", e, exc_info=True
                            )
                            conv.update(["error", str(e)])
                            res = "error"

                        result_queue.put_nowait(res)

                    thread = threading.Thread(target=ask_in_thread)
                    thread.start()

                    async def _stream():
                        # Since we are using an infinite generator, we need to keep track of the stack count to know when to break
                        stack_count = 0
                        for mark, content in conv.stream():
                            json_string = json.dumps([mark, content])

                            # Always yield the update back to the client, as a JSON string
                            yield json_string + "\n"  # NEW LINE DELIMITED JSON, otherwise the client will not be able to read the stream

                            # Keep track of the stack count to know when to break
                            if mark == "start":
                                stack_count += 1
                            elif mark == "end":
                                stack_count -= 1

                            logger.debug("Stack count: %s", stack_count)
                            if stack_count == 0:
                                logger.debug(
                                    "Received response and stack count is 0, breaking stream."
                                )
                                break
                            if mark == "error":
                                logger.debug("Received error, breaking stream.")
                                break

                        thread.join()
                        response = AskResponse(
                            conversation=ConversationResponse(
                                messages=conv.messages,
                                variables=conv.variables,
                                metrics=conv.metrics,
                            ),
                            result=result_queue.get(),
                        ).model_dump()
                        yield json.dumps(["result", response])

                    response = StreamingResponse(
                        _stream(), media_type="application/x-ndjson"
                    )
                else:
                    result = askable.ask(conv, stream=False)
                    response = AskResponse(
                        conversation=ConversationResponse(
                            messages=conv.messages,
                            variables=conv.variables,
                            metrics=conv.metrics,
                        ),
                        result=result,
                    )

                    logger.debug(f"Returning response: {response}")

                return response
            else:
                # Return 404 if the askable is not found
                return {"detail": "Askable not found"}, 404


def find_askables(source_dir: str = None):
    """Find all askables in the given source directory.

    Args:
        source_dir (str): The source directory to search for askables. If None, the current directory is used.
    """
    if source_dir is None:
        source_dir = os.path.dirname(os.path.realpath(__file__))
    askables = []
    for filename in os.listdir(source_dir):
        if filename.endswith("_entry.py") and filename != "main.py":
            module_name = filename[:-3]
            spec = importlib.util.spec_from_file_location(
                module_name, os.path.join(source_dir, filename)
            )
            module = importlib.util.module_from_spec(spec)
            logger.debug(
                f"Loading module {module_name} from {os.path.join(source_dir, filename)}"
            )
            spec.loader.exec_module(module)
            for name in dir(module):
                logger.debug(f"Checking {name}")
                obj = getattr(module, name)
                if isinstance(obj, Askable):
                    logger.debug(f"Found askable: {obj}")
                    askables.append(obj)
    return askables
