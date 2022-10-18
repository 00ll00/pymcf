from typing import Any

from datas.Score import IfScoreRunOp, IfNotScoreRunOp
from datas.datas import InGameData
from operations import CallFunctionOp
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


def new_file():
    MCFContext.new_file()


def finish_file():
    MCFContext.exit_file()


def if_true_run_last_file(var: InGameData):
    if type(var) == Score:
        IfScoreRunOp(var, CallFunctionOp(MCFContext.last_file().name, offline=True))
    else:
        raise RuntimeError()


def if_false_run_last_file(var: InGameData):
    if type(var) == Score:
        IfNotScoreRunOp(var, CallFunctionOp(MCFContext.last_file().name, offline=True))
    else:
        raise RuntimeError()


def convert_return(value: Any):
    MCFContext.assign_return_value(value)
    return value


def load_return_value():
    return MCFContext.get_return_value()
