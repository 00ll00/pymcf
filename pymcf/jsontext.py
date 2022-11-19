import json
from abc import ABC, abstractmethod
from typing import Mapping


class JsonText(ABC):

    @abstractmethod
    def to_str(self):
        ...

    def __str__(self):
        return self.to_str()


class JsonTextComponent(JsonText):

    def __init__(self, data: Mapping):
        self.json = data

    def to_str(self):
        return json.dumps(self.json)


class IJsonText(ABC):

    @property
    @abstractmethod
    def json(self) -> JsonText:
        ...
