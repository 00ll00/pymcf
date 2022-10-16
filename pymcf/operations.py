from pymcf.mcversions import MCVer


class Operation:
    """
    base class of mcfunction operations.

    when an op initialized, it **added to context automatically**.
    """

    def __init__(self):
        from pymcf.context import MCFContext
        MCFContext.append_op(self)

    def gen_code(self, mcver: MCVer) -> str:
        raise NotImplementedError()


class InsertRawOp(Operation):

    def __init__(self, code: str):
        super().__init__()
        self.code = code

    def gen_code(self, mcver: MCVer) -> str:
        return self.code


def raw(code: str):
    if not isinstance(code, str):
        return
    InsertRawOp(code)


class CallFunctionOp(Operation):

    def __init__(self, func_full_name: str):
        super().__init__()
        self.func_full_name = func_full_name

    def gen_code(self, mcver: MCVer) -> str:
        return f"function {self.func_full_name}"
