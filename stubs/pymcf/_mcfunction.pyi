from pymcf._frontend.context import MCFContext as MCFContext
from pymcf._frontend.ast_rewrite import recompile as recompile
from pymcf import logger as logger
from pymcf._project import Project as Project
from pymcf.util import staticproperty as staticproperty
from pymcf.data.data import InGameData as InGameData, InGameObj as InGameObj
from pymcf.operations import CallFunctionOp as CallFunctionOp, CallMethodOp as CallMethodOp
from typing import Set, Callable


class mcfunction:
    def __init__(self, tags: Set[str] | None = ..., is_entry_point: bool = False, inline: bool = False) -> None: ...
    def __call__(self, *args, **kwargs) -> None: ...
        # make mcfunction callable, for type hint only
        # real invoke handler is caller

    load: Callable
    tick: Callable
    manual: Callable
    inline: Callable
