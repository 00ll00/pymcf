from types import FunctionType
from typing import Any


class staticproperty:
    func: FunctionType
    def __init__(self, func) -> None: ...
    def __get__(self, instance, owner): ...

class lazy:
    func: FunctionType
    loaded: bool
    value: Any
    def __init__(self, func) -> None: ...
    def __call__(self, *args, **kwargs): ...
