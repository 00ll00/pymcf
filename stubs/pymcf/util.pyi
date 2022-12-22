from types import FunctionType
from typing import Any, Type


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

def staticclass(cls: Type): ...

Null: object

def create_file_dir(filepath: str): ...