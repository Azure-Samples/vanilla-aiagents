# A common Python interface for both Agent and Team
from abc import ABC, abstractmethod

from .conversation import Conversation


class Askable(ABC):
    """A common interface for both Agent and Team."""

    @abstractmethod
    def ask(self, conversation: Conversation, stream=False) -> str:
        pass

    def __init__(self, id: str, description: str):
        """Initialize the Askable object.

        Args:
            id (str): The ID of the Askable object. Will be used to uniquely identify it.
            description (str): The description of the Askable object. Typically used by orchestrators.
        """
        self._id = id
        self._description = description

    # an id property with a default implementation
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    # a description property with a default implementation
    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value
