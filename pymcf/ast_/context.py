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

    def __init__(self, name: str, env=None, inline: bool = False, return_type: type = _PlaceHolder.NoValue):
        self.name = name
        self.inline = inline
        self.root_scope = Scope()
        self._scope_stack = [self.root_scope]
        self._return_type = return_type  # 指定的返回值类型，为 _PlaceHolder.NoValue 表示自行推断
        self._raw_return_values = []  # 所有原始 return 语句返回的值
        self._return_value: Any = _PlaceHolder.NoValue  # 使用 _PlaceHolder.NoValue 占位，在结束时检查
        self._excs: ExcSet = None  # 使用 None 占位，在结束时检查
        self._finished = False

        if self.inline:
            assert env is None
            curr = _current_ctx.get()
            self.env = curr.env
        else:
            self.env = env

    def __enter__(self):
        assert not self._finished
        self._last_ctx = _current_ctx.get()
        _current_ctx.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # exit 时不能直接调用 self.finish()，存在部分 context 会多次进出
        _current_ctx.set(self._last_ctx)

    def __repr__(self):
        return f"<Context {self.name!r}>"

    @staticmethod
    def current_ctx() -> Optional["Context"]:
        return _current_ctx.get()

    @contextmanager
    def enter_scope(self, scope: Scope | None = None):
        """
        with enter_scope() as scope:
            {build scope content}
        """
        assert not self._finished
        if scope is None:
            scope = Scope()
        self._scope_stack.append(scope)
        try:
            yield scope
        finally:
            self._scope_stack.pop()

    def record_statement(self, stmt: stmt):
        assert not self._finished
        if isinstance(stmt, Raise):
            if isinstance(stmt.exc, RtReturn):
                self.record_return(stmt.exc.value)
            elif stmt.exc is RtReturn:
                self.record_return(None)
        self._scope_stack[-1].flow.append(stmt)

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
                self._return_value = self._return_type.__create_tmp__()
                Assign(self._return_value, value)
        else:
            if self._return_value is _PlaceHolder.CtValue:
                if isinstance(value, RtBaseData) or value != self._raw_return_values[0]:
                    raise TypeError(f"函数存在多个不同的编译期返回值，但未提供运行期返回值数据类型。")
            else:
                Assign(self._return_value, value)

    def finish(self):
        """
        ctx 结束时手动调用，结束后 ctx 不应发生变化
        """
        assert not self._finished
        if self._return_value is _PlaceHolder.NoValue:
            # 没有显式 return，返回值为 None
            self._return_value = None
        elif self._return_value is _PlaceHolder.CtValue:
            # 函数返回单个编译期期值
            self._return_value = self._raw_return_values[0]

        # 消除 RtReturn
        return_catch = Try(
            sc_try=self.root_scope,
            excepts=[ExcHandle((RtReturn,), Scope([]))],
            sc_else=Scope(),
            sc_finally=Scope(),
            _offline=True)
        self.root_scope = Scope([return_catch])

        if self.root_scope.excs.types & {RtContinue, RtBreak}:
            raise SyntaxError(f"函数 {self.name} 中出现脱离循环的运行期循环控制语句")  # TODO 提供具体的代码定位
        self._excs = self.root_scope.excs.remove_subclasses(RtCfExc)

        if self.inline:  # TODO 内联函数返回值处理
            curr = _current_ctx.get()
            for s in self.root_scope.flow:
                curr.record_statement(s)

        self._finished = True

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

_current_ctx: ContextVar[Context | None] = ContextVar("_current_ctx", default=None)
