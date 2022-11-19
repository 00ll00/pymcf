from typing import Any, Callable, Set

from pymcf import breaklevel
from pymcf.datas.nbt import Nbt
from pymcf.datas.score import IfScoreGEValueRunOp, IfScoreLTValueRunOp, ScoreSetValueOp
from pymcf.datas.datas import InGameData
from pymcf.operations import CallFunctionOp, ExecuteOp
from pymcf.context import MCFContext, MCFFile
from pymcf.datas import Score


def convert_assign(value: Any, var: Any):
    """
    for score assignment: s = 1
    """
    if isinstance(var, Score):
        var.set(value)
        return var
    elif isinstance(var, Nbt):
        var._set_value(value)
    else:
        return value


def new_file():
    MCFContext.new_file()


def exit_file():
    MCFContext.exit_file()


def get_current_file():
    return MCFContext.current_file()


def exit_and_call_files_until(current: MCFFile):
    while MCFContext.current_file() is not current:
        MCFContext.exit_file()
        CallFunctionOp(MCFContext.last_file().name)


def gen_run_file_on_condition(file_getter: Callable[[], MCFFile], on_true: bool, brk_flags: Set[Score],
                              break_level: int = breaklevel.NONE) -> Callable[[InGameData], None]:
    """
    generate conditional mcfunction call operation.

    :param file_getter: return a mcfunction file on call
    :param on_true: call on true if True
    :param brk_flags: break flag score var.  0: nothing  1: continue  2: break  3: return
    :param break_level: call while all brk_flag not greater than this value
    :return: operation generator
    """
    run_op = IfScoreGEValueRunOp if on_true else IfScoreLTValueRunOp

    def f(var: InGameData):
        if type(var) == Score:
            run = run_op(var, 1, CallFunctionOp(file_getter().name, offline=True), offline=True)
        else:
            raise ValueError()

        for flag in brk_flags:
            run = IfScoreLTValueRunOp(flag, break_level + 1, run, offline=True)
        ExecuteOp(run)

    return f


def gen_run_last_file_while(on_true: bool, brk_flags: Set[Score], break_level: int = breaklevel.NONE) -> Callable[
    [InGameData], None]:
    return gen_run_file_on_condition(MCFContext.last_file, on_true, brk_flags, break_level)


def gen_run_curr_file_while(on_true: bool, brk_flags: Set[Score], break_level: int = breaklevel.NONE) -> Callable[
    [InGameData], None]:
    return gen_run_file_on_condition(MCFContext.current_file, on_true, brk_flags, break_level)


def gen_run_outer_file_while(on_true: bool, brk_flags: Set[Score], break_level: int = breaklevel.NONE) -> Callable[
    [InGameData], None]:
    return gen_run_file_on_condition(MCFContext.outer_file, on_true, brk_flags, break_level)


def gen_run_last_file(brk_flags: Set[Score], break_level: int = breaklevel.NONE) -> Callable:
    def f():
        run = CallFunctionOp(MCFContext.last_file().name, offline=True)
        for brk_flag in brk_flags:
            run = IfScoreLTValueRunOp(brk_flag, break_level + 1, run, offline=True)
        ExecuteOp(run)

    return f


def gen_run_curr_file(brk_flags: Set[Score], break_level: int = breaklevel.NONE) -> Callable:
    def f():
        run = CallFunctionOp(MCFContext.current_file().name, offline=True)
        for brk_flag in brk_flags:
            run = IfScoreLTValueRunOp(brk_flag, break_level + 1, run, offline=True)
        ExecuteOp(run)

    return f


def gen_run_outer_file(brk_flags: Set[Score], break_level: int = breaklevel.NONE) -> Callable:
    def f():
        run = CallFunctionOp(MCFContext.outer_file().name, offline=True)
        for brk_flag in brk_flags:
            run = IfScoreLTValueRunOp(brk_flag, break_level + 1, run, offline=True)
        ExecuteOp(run)

    return f


def convert_return(value: Any):
    MCFContext.assign_return_value(value)
    return value


def load_return_value():
    return MCFContext.get_return_value()


def gen_set_score(score: Score, value: Any):
    return lambda: score.set(value)


def gen_set_score_value_while(target: Score, value: int, on_true: bool):
    run_op = IfScoreGEValueRunOp if on_true else IfScoreLTValueRunOp

    def f(var: InGameData):
        if type(var) == Score:
            run_op(var, 1, ScoreSetValueOp(target, value, offline=True))
        else:
            raise ValueError()

    return f
