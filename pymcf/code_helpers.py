from typing import Any

from pymcf.context import MCFContext
from pymcf.datas import Score


def convert_assign(value: Any, var: Any):
    """
    for score assignment: s = 1
    """
    if isinstance(var, Score):
        var.set(value)
        return var
    else:
        return value


def finish_file():
    """
    for return
    """
    MCFContext.finish_file()
