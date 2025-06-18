import ast
from abc import abstractmethod
from typing import Any, Self

from pymcf.ast_ import operation, compiler_hint


class code_block(ast.AST):
    def __init__(self, name: str):
        self.name = name
        self.attributes = {}

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
        super().__init__(name)
        self.ops: list[operation | compiler_hint] = []
        self.cond: Any = None  # 判断条件

        self.direct: code_block | None = None  # 位于 ops 之后，cond 判断之前无执行
        self.false: code_block | None = None  # 在 direct 之后若 cond 判断为假则执行
        self.true: code_block | None = None  # 在 direct 之后若 cond 判断为真则执行

    def add_op(self, op):
        self.ops.append(op)


class jmpop(ast.AST):
    _fields = ("target", )
    # 均要具有 target 字段指向跳转的 block，target 为 None 表示匹配成功时仅中断匹配流程而没有进一步动作
    def __init__(self, target: code_block | None):
        self.target = target


class JmpEq(jmpop):
    _fields = ("value", "target")
    def __init__(self, value: Any, target: code_block):
        super().__init__(target)
        self.value = value


class JmpNotEq(jmpop):
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
        super().__init__(name)
        self.flag = flag
        self.cases = cases
        self.inactive = inactive  # 用于指示分支完成后的值，应避免被各分支条件响应  TODO 好像没什么用


class IrBlockAttr(compiler_hint):
    _attributes = ("attr", )
    def __init__(self, attr: dict, **kwargs):
        self.attr = attr
        super().__init__(**kwargs)
