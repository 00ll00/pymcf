from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from .runtime import RtBaseData
from .syntactic import Scope, stmt, Assign, Raise, RtReturn, ExcSet, RtCfExc, Try, ExcHandle


_PlaceHolder = object()


class Context:

    def __init__(self, name: str, inline: bool = False):
        self.name = name
        self.inline = inline
        self.root_scope = Scope()
        self._scope_stack = [self.root_scope]
        self._tmp_id = 0
        self._tmps = []
        self._return_value: Optional[RtBaseData] = _PlaceHolder  # 使用 _PlaceHolder 占位，在结束时检查
        self._excs: ExcSet = _PlaceHolder  # 使用 _PlaceHolder 占位，在结束时检查
        self._finished = False

        if self.inline:
            curr = _current_ctx.get()
            self._tmp_id = curr._tmp_id

    def __enter__(self):
        assert not self._finished
        self._last_ctx = _current_ctx.get()
        _current_ctx.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # exit 时不能直接调用 self.finish()，存在部分 context 会多次进出
        _current_ctx.set(self._last_ctx)

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

    def record_return(self, value: RtBaseData | None):
        if value is not None and not isinstance(value, RtBaseData):
            raise TypeError(f"包装函数返回值需要是 RtBaseData 或 None，得到了 {type(value)}")
        if self._return_value is _PlaceHolder:
            if value is None:
                self._return_value = None
            else:
                self._return_value = value.__create_tmp__()
        Assign(self._return_value, value)  # TODO RtData返回值是否允许赋值None

    def finish(self):
        """
        ctx 结束时手动调用，结束后 ctx 不应发生变化
        """
        assert not self._finished
        if self._return_value is _PlaceHolder:
            self._return_value = None
        self._excs = self.root_scope.excs.remove_subclasses(RtCfExc)

        if self.inline:  # TODO 内联函数返回值处理
            curr = _current_ctx.get()
            curr._tmp_id = self._tmp_id
            curr._tmps.extend(self._tmps)
            curr.record_statement(Try(
                sc_try=self.root_scope,
                excepts=[ExcHandle((RtReturn,), Scope([]))],
                sc_else=Scope(),
                sc_finally=Scope(),
                excs=self._excs,
                _offline=True))

        self._finished = True

    def new_tmp_id(self) -> int:
        assert not self._finished
        self._tmp_id += 1
        return self._tmp_id

    @property
    def finished(self) -> bool:
        return self._finished
    @property
    def excs(self) -> ExcSet:
        assert self._finished
        return self._excs
    @property
    def return_value(self) -> RtBaseData:
        assert self._finished
        return self._return_value

_current_ctx: ContextVar[Context | None] = ContextVar("_current_ctx", default=None)
