import abc
from abc import ABC, abstractmethod
from typing import Mapping, Sequence, Any


class JsonText(ABC, metaclass=abc.ABCMeta):
    @staticmethod
    def convert_from(value: Any) -> JsonText: ...
    @abstractmethod
    def to_str(self) -> str: ...

class JsonTextComponent(JsonText):
    data: Mapping
    def __init__(self, data: Mapping) -> None: ...
    def to_str(self) -> str: ...


class JsonTextList(JsonText):
    data: Sequence
    def __init__(self, data: Sequence): ...
    def to_str(self) -> str: ...


class JsonTextString(JsonText):
    value: str
    def __init__(self, value: str): ...
    def to_str(self) -> str: ...

class IJsonText(ABC, metaclass=abc.ABCMeta):
    @property
    @abstractmethod
    def json(self) -> JsonText: ...
