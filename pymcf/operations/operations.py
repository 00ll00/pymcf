from abc import ABC

from pymcf.project import Project
from pymcf.mcversions import MCVer


class Operation(ABC):
    """
    base class of mcfunction operations.

    when an online op initialized, it **added to context automatically**.
    """

    def __init__(self, offline: bool = False):
        self.offline: bool = offline
        if not offline:
            from pymcf._frontend.context import MCFContext
            MCFContext.append_op(self)

    def get_length(self, mcver: MCVer) -> int:
        return 1

    def gen_code(self, mcver: MCVer) -> str:
        raise NotImplementedError()

    def __repr__(self):
        return self.gen_code(MCVer.JE_1_19_2)


class InsertRawOp(Operation):

    def __init__(self, code: str, offline: bool = False):
        self.code = code
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return self.code


def raw(code: str):
    if not isinstance(code, str):
        return
    InsertRawOp(code)


class CallFunctionOp(Operation):

    def __init__(self, func_full_name: str, offline: bool = False):
        self.func_full_name = func_full_name
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"function {Project.namespace}:{self.func_full_name}"


class CallMethodOp(Operation):

    def __init__(self, origin_identifier, func_full_name: str, offline: bool = False):
        self.origin_identifier = origin_identifier
        self.func_full_name = func_full_name
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute as {self.origin_identifier} at @s rotated as @s run function {Project.namespace}:{self.func_full_name}"
