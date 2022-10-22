from pymcf.mcversions import MCVer


class Operation:
    """
    base class of mcfunction operations.

    when an online op initialized, it **added to context automatically**.
    """

    def __init__(self, offline: bool = False):
        self.offline: bool = offline
        if not offline:
            from pymcf.context import MCFContext
            MCFContext.append_op(self)

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
        return f"function {self.func_full_name}"


class ExecuteOp(Operation):

    def __init__(self, op: Operation, offline: bool = False):
        self.op = op
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return self.op.gen_code(mcver)
