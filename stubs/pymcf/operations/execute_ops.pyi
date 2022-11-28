from . import Operation as Operation
from .. import MCVer as MCVer

class ExecuteOp(Operation):
    op: Operation
    def __init__(self, op: Operation, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...
