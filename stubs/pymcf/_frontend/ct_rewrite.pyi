from types import CodeType

class CodeTypeRewriter:
    codetype: CodeType
    def __init__(self, ct: CodeType, rewrite_return: bool = True) -> None: ...

