from typing import Any, Self

from .runtime import RtContinue, RtBreak
from .syntactic import Block, stmt, ExcSet


class Scope:

    _all: list[Self] = []

    def __init__(self, name: str, set_throws=None):
        Scope._all.append(self)

        self.name = name
        self.namespace = None  # TODO

        self._return_value = None

        self._root_block = Block()
        self._block_stack = [self._root_block]

        self._excs = None if set_throws is None else ExcSet(set_throws)
        self._finished = False

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"

    @property
    def finished(self) -> bool:
        return self._finished

    def enter_block(self, block: Block = None):
        if block is None:
            block = Block()
        self._block_stack.append(block)
        return block

    def pop_block(self):
        return self._block_stack.pop()

    @property
    def current_block(self):
        return self._block_stack[-1]

    def record_stmt(self, st: stmt):
        self._block_stack[-1].flow.append(st)

    @property
    def excs(self) -> ExcSet:
        assert self._excs is not None
        return self._excs

    @property
    def excs_or_none(self) -> ExcSet | None:
        # 当 scope 未完成且未指定抛出异常类型时会返回 None
        return self._excs

    @property
    def return_value(self) -> Any:
        assert self.finished
        return self._return_value

    def finish(self):
        assert not self._finished

        if self._root_block.excs.types & {RtContinue, RtBreak}:
            raise SyntaxError(f"函数 {self.name} 中出现脱离循环的运行期循环控制语句")  # TODO 提供具体的代码定位
        if self._excs is None:
            self._excs = self._root_block.excs

        self._finished = True

