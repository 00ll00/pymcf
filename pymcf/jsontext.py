import json
from abc import ABC, abstractmethod
from typing import Mapping, Sequence


class JsonText(ABC):

    @abstractmethod
    def to_str(self):
        ...

    def __str__(self):
        return self.to_str()


class JsonTextComponent(JsonText):

    def __init__(self, data: Mapping):
        self.data = data

    def to_str(self):
        return json.dumps(self.data)


class JsonTextList(JsonText):

    def __init__(self, data: Sequence):
        self.data = list(data)

    def to_str(self):
        return json.dumps(self.data)


class IJsonText(ABC):

    @property
    @abstractmethod
    def json(self) -> JsonText:
        ...
