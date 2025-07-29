from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from typing import Optional, Any

from .runtime import RtBaseVar, RtReturn
from .scope import Scope
from .syntactic import Block, stmt, Assign, Raise, Try, ExcHandle

NoValue = object()
CtValue = object()


class Constructor:

    def __init__(self, name: str, scope: Scope, inline: bool = False, return_type: type = NoValue):
        self.name = name
        self.inline = inline
        self.scope = scope

        self._raw_return_values = []
        self._return_type = return_type
        self._return_value = NoValue

        # add RtReturn catcher
        return_caught = Block()
        self.scope.record_stmt(Try(
            blk_try=return_caught,
            excepts=[ExcHandle((RtReturn,), Block([]))],
            blk_else=Block(),
            blk_finally=Block(),
            _offline=True))
        self.scope.enter_block(return_caught)

        self._finished = False

    def __enter__(self):
        assert not self.finished
        self._last_constr = _current_constr.get()
        _current_constr.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # exit 时不能直接调用 self.finish()，存在部分 constructor 会多次进出
        _current_constr.set(self._last_constr)

    def __repr__(self):
        return f"<Constructor {self.name!r}>"

    @staticmethod
    def current_constr() -> Optional["Constructor"]:
        return _current_constr.get()

    @contextmanager
    def enter_block(self, block: Block | None = None):
        """
        with enter_block() as block:
            {build block content}
        """
        assert not self.finished
        block = self.scope.enter_block(block)
        try:
            yield block
        finally:
            self.scope.pop_block()

    def record_statement(self, st: stmt):
        assert not self.finished
        if isinstance(st, Raise):
            if isinstance(st.exc, RtReturn):
                self.record_return(st.exc.value)
            elif st.exc is RtReturn:
                self.record_return(None)
        self.scope.record_stmt(st)

    def record_return(self, value):
        self._raw_return_values.append(deepcopy(value))
        if self._return_value is NoValue:
            # 未记录返回值
            if self._return_type is NoValue:  # 未提供返回值类型
                if isinstance(value, RtBaseVar):
                    self._return_value = value.__create_var__()
                    Assign(self._return_value, value)
                else:
                    self._return_value = CtValue
            else:
                assert issubclass(self._return_type, RtBaseVar)
                self._return_value = self._return_type.__create_var__()
                Assign(self._return_value, value)
        else:
            if self._return_value is CtValue:
                if isinstance(value, RtBaseVar) or value != self._raw_return_values[0]:
                    raise TypeError(f"函数存在多个不同的编译期返回值，但未提供运行期返回值数据类型。")
            else:
                Assign(self._return_value, value)

    def finish(self):
        """
        constructor 结束时手动调用，结束后 constructor 可被释放
        """
        assert not self.finished

        # 弹出 RtReturn catcher
        self.scope.pop_block()

        if self._return_value is NoValue:
            # 没有显式 return，返回值为 None
            self._return_value = None
        elif self._return_value is CtValue:
            # 函数返回单个编译期期值
            self._return_value = self._raw_return_values[0]

        if not self.inline:
            self.scope._return_value = self._return_value
            self.scope.finish()

        self._finished = True

    @property
    def finished(self) -> bool:
        return self._finished
    @property
    def return_value(self) -> Any:
        if not self.finished:
            return NoValue  # TODO
        return self._return_value

_current_constr: ContextVar[Constructor | None] = ContextVar("_current_constr", default=None)
