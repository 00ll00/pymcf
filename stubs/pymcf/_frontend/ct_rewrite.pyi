from types import CodeType

class CodeTypeRewriter:
    codetype: CodeType
    def __init__(self, ct: CodeType, lineno: int | None = None) -> None: ...

