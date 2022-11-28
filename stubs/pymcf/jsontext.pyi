import abc
from abc import ABC, abstractmethod
from typing import Mapping

class JsonText(ABC, metaclass=abc.ABCMeta):
    @abstractmethod
    def to_str(self): ...

class JsonTextComponent(JsonText):
    data: Mapping
    def __init__(self, data: Mapping) -> None: ...
    def to_str(self): ...

class IJsonText(ABC, metaclass=abc.ABCMeta):
    @property
    @abstractmethod
    def json(self) -> JsonText: ...
