# Askable

The `Askable` class is an abstract base class for objects that can be asked questions. It defines the interface for asking questions, with an id and a description.

All other classes inherit from `Askable`.

## Tips

* ID is used to identify the askable in the conversation.
* Description is used to help orchestrators deduce which Askable to use.
* One common use case to subclass `Askable` is to create a helper block in Sequence to ensure a pre or post step is always performed.

## Usage

```python
from vanilla_aiagents.askable import Askable

class MyAskable(Askable):
    def __init__(self, id, description):
        super().__init__(id, description)

    def ask(self, conversation, stream=False):
        # Implementation here
```

## Methods

### `ask(conversation: Conversation, stream: bool) -> None`

parameters:

- `conversation` (Conversation): The conversation to ask the question in.
- `stream` (bool): Whether to stream the response or not.