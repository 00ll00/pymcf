import json
import typing
from abc import ABC, abstractmethod
from typing import Mapping, Sequence, Any


class JsonText(ABC):

    @staticmethod
    def convert_from(value: Any) -> "JsonText":
        if value is None:
            return JsonTextString("")
        elif isinstance(value, JsonText):
            return value
        elif isinstance(value, Mapping):
            return JsonTextComponent(value)
        elif isinstance(value, str):
            return JsonTextString(value)
        elif isinstance(value, Sequence):
            return JsonTextList(value)
        else:
            return JsonTextString(str(value))

    @abstractmethod
    def to_str(self) -> str:
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


class JsonTextString(JsonText):

    def __init__(self, value: str):
        self.value = value

    def to_str(self):
        return json.dumps(self.value)


class IJsonText(ABC):

    @property
    @abstractmethod
    def json(self) -> JsonText:
        ...
