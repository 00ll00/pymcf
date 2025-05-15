import ast
from abc import abstractmethod
from typing import Any, Self

from ast_ import operation, compiler_hint


class code_block(ast.AST):
    @abstractmethod
    def simplified(self) -> Self | None:
        """
        简化代码块，返回简化后的代码块

        若此代码块能够被跳过，则返回应当跳转到的代码块或 None，否则返回自身
        """


class BasicBlock(code_block):
    """
    基础流程块，按以下顺序执行

    1. 按顺序执行 self.ops 中的操作
    2. 直接跳转到 self.direct
    3. 判断 self.cond，选择下一个跳转的块为 self.true 或 self.false
    """
    _fields = ("ops", "direct", "cond", "false", "true")
    _attributes = ("name", "attributes", )
    def __init__(self, name: str):
        self.name = name
        self.ops: list[operation | compiler_hint] = []
        self.cond: Any = None  # 判断条件

        self.direct: code_block | None = None  # 位于 ops 之后，cond 判断之前无执行
        self.false: code_block | None = None  # 在 direct 之后若 cond 判断为假则执行
        self.true: code_block | None = None  # 在 direct 之后若 cond 判断为真则执行

        self.attributes = {}

    def add_op(self, op):
        self.ops.append(op)

    def simplified(self) -> Self | None:
        if self.true is None and self.false is None:
            self.cond = None
        if len(self.ops) == 0 and self.cond is None:
                # 不应存在全空的环路
                return self.direct
        if self.cond is not None:
            # 跳过相同条件的空块
            if isinstance(self.true, BasicBlock) and self.true.cond is self.cond and len(self.true.ops) == 0 and self.true.direct is None:
                self.true = self.true.true
            if isinstance(self.false, BasicBlock) and self.false.cond is self.cond and len(self.false.ops) == 0 and self.false.direct is None:
                self.false = self.false.false
        return self


class jmpop(ast.AST):
    _fields = ("target", )
    # 均要具有 target 字段指向跳转的 bloc
    def __init__(self, target: code_block):
        self.target = target


class JmpEq(jmpop):
    _fields = ("value", "target")
    def __init__(self, value: Any, target: code_block):
        super().__init__(target)
        self.value = value


class JmpNeq(jmpop):
    _fields = ("value", "target")
    def __init__(self, value: Any, target: code_block):
        super().__init__(target)
        self.value = value


class MatchJump(code_block):
    """
    选择跳转逻辑块

    根据 flag，选择第一个符合条件的 case 进行跳转

    inactivate 表示跳转后应当为 flag（副本）设置值，避免其余分支响应
    """
    _fields = ("flag", "cases", "inactive")
    _attributes = ("name", "attributes")
    def __init__(self, flag: Any, cases: list[jmpop], inactive: Any = 0, name: str = None):
        self.name = name
        self.flag = flag
        self.cases = cases
        self.inactive = inactive  # 用于指示分支完成后的值，应避免被各分支条件响应

    def simplified(self) -> Self | None:
        if len(self.cases) == 0:
            return None
        # 无跳转目标的case暂时不能删除，可能存在flag清除的作用
        return self