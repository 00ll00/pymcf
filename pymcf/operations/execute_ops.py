from . import Operation
from .. import MCVer


class ExecuteOp(Operation):
    """
    execute an operation. use this to make an operation online.
    """

    def __init__(self, op: Operation, offline: bool = False):
        self.op = op
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return self.op.gen_code(mcver)
