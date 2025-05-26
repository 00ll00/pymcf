from abc import ABC, abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from typing import Optional, Any

from .runtime import RtBaseData, RtContinue, RtBreak, RtReturn, RtCfExc
from .syntactic import Scope, stmt, Assign, Raise, ExcSet, Try, ExcHandle


class _PlaceHolder:
    NoValue = object()
    CtValue = object()


class Context:

    def __init__(self, name: str):
        self.name = name
        self.locals = []

        self.rt_args = {}
        self.returns = None

        self.root_scope = Scope()
        self._scope_stack = [self.root_scope]

        self._finished = False

    def record_stmt(self, st: stmt):
        self._scope_stack[-1].flow.append(st)

    def

class Constructor:

    def __init__(self, name: str, ctx: Context, inline: bool = False, return_type: type = _PlaceHolder.NoValue):
        self.name = name
        self.inline = inline
        self.ctx = ctx

        self._raw_return_values = []
        self._return_type = return_type

    def begin(self):
        # add RtReturn catcher
        return_catched = Scope()
        self.ctx.record_stmt(Try(
            sc_try=return_catched,
            excepts=[ExcHandle((RtReturn,), Scope([]))],
            sc_else=Scope(),
            sc_finally=Scope(),
            _offline=True))
        self.ctx._scope_stack.append(return_catched)


    def __enter__(self):
        assert not self._finished
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
    def enter_scope(self, scope: Scope | None = None):
        """
        with enter_scope() as scope:
            {build scope content}
        """
        assert not self._finished
        if scope is None:
            scope = Scope()
        self.ctx._scope_stack.append(scope)
        try:
            yield scope
        finally:
            self.ctx._scope_stack.pop()

    def record_statement(self, st: stmt):
        assert not self._finished
        if isinstance(st, Raise):
            if isinstance(st.exc, RtReturn):
                self.record_return(st.exc.value)
            elif st.exc is RtReturn:
                self.record_return(None)
        self.ctx.record_stmt(st)

    def record_return(self, value):
        self._raw_return_values.append(deepcopy(value))
        if self._return_value is _PlaceHolder.NoValue:
            # 未记录返回值
            if self._return_type is _PlaceHolder.NoValue:  # 未提供返回值类型
                if isinstance(value, RtBaseData):
                    self._return_value = value.__create_var__()
                    Assign(self._return_value, value)
                else:
                    self._return_value = _PlaceHolder.CtValue
            else:
                self._return_value = self._return_type.__create_var__()
                Assign(self._return_value, value)
        else:
            if self._return_value is _PlaceHolder.CtValue:
                if isinstance(value, RtBaseData) or value != self._raw_return_values[0]:
                    raise TypeError(f"函数存在多个不同的编译期返回值，但未提供运行期返回值数据类型。")
            else:
                Assign(self._return_value, value)

    def finish(self):
        """
        constructor 结束时手动调用，结束后 constructor 可被释放
        """
        assert not self.ctx._finished

        # 弹出 RtReturn catcher
        self.ctx._scope_stack.pop()

        if self._return_value is _PlaceHolder.NoValue:
            # 没有显式 return，返回值为 None
            self._return_value = None
        elif self._return_value is _PlaceHolder.CtValue:
            # 函数返回单个编译期期值
            self._return_value = self._raw_return_values[0]

        # 消除 RtReturn
        return_catch = Try(
            sc_try=self.ctx.root_scope,
            excepts=[ExcHandle((RtReturn,), Scope([]))],
            sc_else=Scope(),
            sc_finally=Scope(),
            _offline=True)
        self.ctx.root_scope = Scope([return_catch])

        if self.root_scope.excs.types & {RtContinue, RtBreak}:
            raise SyntaxError(f"函数 {self.name} 中出现脱离循环的运行期循环控制语句")  # TODO 提供具体的代码定位
        self._excs = self.root_scope.excs.remove_subclasses(RtCfExc)

        if self.inline:  # TODO 内联函数返回值处理
            curr = _current_constr.get()
            for s in self.root_scope.flow:
                curr.record_statement(s)

        self.ctx_finished = True

    @property
    def finished(self) -> bool:
        return self._finished
    @property
    def excs(self) -> ExcSet:
        assert self._finished
        return self._excs
    @property
    def return_value(self) -> Any:
        assert self._finished
        return self._return_value

_current_constr: ContextVar[Constructor | None] = ContextVar("_current_constr", default=None)
