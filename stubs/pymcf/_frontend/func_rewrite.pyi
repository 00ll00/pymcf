from types import FunctionType, CodeType
from typing import Tuple, Dict, Any


def recompile(func: FunctionType) -> Tuple[CodeType, Dict[str, Any]]: ...
