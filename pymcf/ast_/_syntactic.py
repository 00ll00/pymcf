import ast
from abc import ABC, abstractmethod
from ast import AST as _AST, unaryop, UAdd, USub, Not, Invert, boolop, And, Or, operator, Add, Sub, Mult, Div, FloorDiv, Mod, \
    Pow, LShift, RShift, BitOr, BitXor, BitAnd, MatMult, Is, IsNot, In, NotIn
from functools import reduce
from types import GenericAlias
from typing import Any, Iterable, Self

from .runtime import ExcSet, RtBaseData, RtStopIteration, RtContinue, RtBreak, RtBaseExc, _TBaseRtExc


_NOT_FOUND = object()


class cached_property:
    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        self.__module__ = func.__module__

    def __set_name__(self, owner, name):
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({self.attrname!r} and {name!r})."
            )

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it.")
        try:
            cache = instance._cache
        except AttributeError:
            msg = (
                f"No '_cache' attribute on {type(instance).__name__!r} "
                f"instance to cache {self.attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            val = self.func(instance)
            try:
                cache[self.attrname] = val
            except TypeError:
                msg = (
                    f"The '_cache' attribute on {type(instance).__name__!r} instance "
                    f"does not support item assignment for caching {self.attrname!r} property."
                )
                raise TypeError(msg) from None
        return val

    __class_getitem__ = classmethod(GenericAlias)


class AST(_AST):

    def __init__(self):
        self._cache = {}

    def clear_cache(self):
        self._cache.clear()


class stmt(AST):

    @property
    @abstractmethod
    def excs(self) -> ExcSet:
        ...

    def __init__(self, *_, _offline: bool = None, **__):
        super().__init__()
        if not _offline:
            from .context import Context
            ctx = Context.current_ctx()
            if ctx is None and _offline is not None:
                raise RuntimeError(f"{self!r} 在线操作生成时未处于任何构建上下文中。")
            ctx.record_statement(self)


class Scope(AST):
    _fields = ("flow",)

    def __init__(self, flow: Iterable[stmt] = None):
        self.flow: list[stmt] = list(flow) if flow is not None else []
        super().__init__()

    @cached_property
    def excs(self) -> ExcSet:
        if self.flow:
            s = reduce(lambda a, b: a | b, (st.excs.types for st in self.flow), set())
            if self.flow[-1].excs.always:
                s.discard(None)  # 若 flow 最后一个语句一定引发异常，则整个 scope 必然引发异常
            return ExcSet(s)
        else:
            return ExcSet.EMPTY


class compiler_hint(stmt, ABC):
    """
    compiler_hint 用于提示编译器调整编译策略
    """
    excs = ExcSet.EMPTY


class operation(stmt, ABC):
    """
    operation 不会改变控制流，也不包含控制流
    """
    _reads = ()
    _writes = ()
    excs = ExcSet.EMPTY

    @cached_property
    def reads(self) -> tuple[RtBaseData, ...]:
        res = []
        for k in self._reads:
            v = getattr(self, k)
            if isinstance(v, RtBaseData):
                res.append(v)
        return tuple(res)

    @cached_property
    def writes(self) -> tuple[RtBaseData, ...]:
        res = []
        for k in self._writes:
            v = getattr(self, k)
            assert isinstance(v, RtBaseData)
            res.append(v)
        return tuple(res)


class control_flow(stmt, ABC):
    """
    control_flow 实现控制流语句
    """


class FormattedData:

    def __init__(self, data: RtBaseData, fmt: str | None = None):
        self.data = data
        self.fmt = fmt

    def __repr__(self):
        return f"${{{self.data!r}{f':{self.fmt}' if self.fmt is not None else ''}}}"


class Raw(operation):
    _fields = ("code",)
    def __init__(self, *code: list[str | FormattedData], **kwargs):
        self.code = code
        super().__init__(**kwargs)

    # TODO Raw 是否需要提供读写变量
    reads = ()
    writes = ()


class Assign(operation):
    _fields = ("target", "value")
    _reads = ("value",)
    _writes = ("target",)
    def __init__(self, target, value, *args, **kwargs):
        self.target = target
        self.value = value
        super().__init__(*args, **kwargs)


class UnaryOp(operation):
    _fields = ("op", "target", "value")
    _reads = ("value",)
    _writes = ("target",)
    def __init__(self, op: unaryop, target, value, *args, **kwargs):
        self.op = op
        self.target = target
        self.value = value
        super().__init__(*args, **kwargs)

    @staticmethod
    def UAdd(target, value, *args, **kwargs):
        return UnaryOp(UAdd(), target, value, *args, **kwargs)

    @staticmethod
    def USub(target, value, *args, **kwargs):
        return UnaryOp(USub(), target, value, *args, **kwargs)

    @staticmethod
    def Not(target, value, *args, **kwargs):
        return UnaryOp(Not(), target, value, *args, **kwargs)

    @staticmethod
    def Invert(target, value, *args, **kwargs):
        return UnaryOp(Invert(), target, value, *args, **kwargs)


class Inplace(operation):
    """
    target = target <op> value
    """
    _fields = ("op", "target", "value")
    _reads = ("target", "value")
    _writes = ("target",)
    def __init__(self, op: operator | boolop, target, value, *args, **kwargs):
        self.op = op
        self.target = target
        self.value = value
        super().__init__(*args, **kwargs)

    @staticmethod
    def And(target, value, *args, **kwargs):
        return Inplace(And(), target, value, *args, **kwargs)

    @staticmethod
    def Or(target, value, *args, **kwargs):
        return Inplace(Or(), target, value, *args, **kwargs)

    @staticmethod
    def Add(target, value, *args, **kwargs):
        return Inplace(Add(), target, value, *args, **kwargs)

    @staticmethod
    def Sub(target, value, *args, **kwargs):
        return Inplace(Sub(), target, value, *args, **kwargs)

    @staticmethod
    def Mult(target, value, *args, **kwargs):
        return Inplace(Mult(), target, value, *args, **kwargs)

    @staticmethod
    def Div(target, value, *args, **kwargs):
        return Inplace(Div(), target, value, *args, **kwargs)

    @staticmethod
    def FloorDiv(target, value, *args, **kwargs):
        return Inplace(FloorDiv(), target, value, *args, **kwargs)

    @staticmethod
    def Mod(target, value, *args, **kwargs):
        return Inplace(Mod(), target, value, *args, **kwargs)

    @staticmethod
    def Pow(target, value, *args, **kwargs):
        return Inplace(Pow(), target, value, *args, **kwargs)

    @staticmethod
    def LShift(target, value, *args, **kwargs):
        return Inplace(LShift(), target, value, *args, **kwargs)

    @staticmethod
    def RShift(target, value, *args, **kwargs):
        return Inplace(RShift(), target, value, *args, **kwargs)

    @staticmethod
    def BitOr(target, value, *args, **kwargs):
        return Inplace(BitOr(), target, value, *args, **kwargs)

    @staticmethod
    def BitXor(target, value, *args, **kwargs):
        return Inplace(BitXor(), target, value, *args, **kwargs)

    @staticmethod
    def BitAnd(target, value, *args, **kwargs):
        return Inplace(BitAnd(), target, value, *args, **kwargs)

    @staticmethod
    def MatMult(target, value, *args, **kwargs):
        return Inplace(MatMult(), target, value, *args, **kwargs)


class cmpop(ast.cmpop):

    @abstractmethod
    def opposite(self) -> Self: ...


class Eq(cmpop):
    def opposite(self) -> Self:
        return self

class NotEq(cmpop):
    def opposite(self) -> Self:
        return self

class Lt(cmpop):
    def opposite(self) -> Self:
        return Gt()

class LtE(cmpop):
    def opposite(self) -> Self:
        return GtE()

class Gt(cmpop):
    def opposite(self) -> Self:
        return Lt()

class GtE(cmpop):
    def opposite(self) -> Self:
        return LtE()

class Compare(operation):
    _fields = ("op", "target", "left", "right")
    _reads = ("left", "right")
    _writes = ("target",)
    def __init__(self, op: cmpop, target, left, right, *args, **kwargs):
        self.op = op
        self.target = target
        self.left = left
        self.right = right
        super().__init__(*args, **kwargs)

    @staticmethod
    def Eq(target, left, right, *args, **kwargs):
        return Compare(Eq(), target, left, right, *args, **kwargs)

    @staticmethod
    def NotEq(target, left, right, *args, **kwargs):
        return Compare(NotEq(), target, left, right, *args, **kwargs)

    @staticmethod
    def Lt(target, left, right, *args, **kwargs):
        return Compare(Lt(), target, left, right, *args, **kwargs)

    @staticmethod
    def LtE(target, left, right, *args, **kwargs):
        return Compare(LtE(), target, left, right, *args, **kwargs)

    @staticmethod
    def Gt(target, left, right, *args, **kwargs):
        return Compare(Gt(), target, left, right, *args, **kwargs)

    @staticmethod
    def GtE(target, left, right, *args, **kwargs):
        return Compare(GtE(), target, left, right, *args, **kwargs)

    # @staticmethod
    # def Is(target, left, right, *args, **kwargs):
    #     return Compare(Is(), target, left, right, *args, **kwargs)
    #
    # @staticmethod
    # def IsNot(target, left, right, *args, **kwargs):
    #     return Compare(IsNot(), target, left, right, *args, **kwargs)
    #
    # @staticmethod
    # def In(target, left, right, *args, **kwargs):
    #     return Compare(In(), target, left, right, *args, **kwargs)
    #
    # @staticmethod
    # def NotIn(target, left, right, *args, **kwargs):
    #     return Compare(NotIn(), target, left, right, *args, **kwargs)


class If(control_flow):
    _fields = ("condition", "sc_body", "sc_else")
    def __init__(self, condition: Any, sc_body: Scope, sc_else: Scope, *args, **kwargs):
        self.condition = condition
        self.sc_body = sc_body
        self.sc_else = sc_else
        super().__init__(*args, **kwargs)

    @cached_property
    def excs(self) -> ExcSet:
        return ExcSet(self.sc_body.excs.types | self.sc_else.excs.types)


class For(control_flow):
    _fields = ("iterator", "sc_iter", "sc_body", "sc_else")
    def __init__(self, iterator: Any, sc_iter: Scope, sc_body: Scope, sc_else: Scope, *args, **kwargs):
        self.iterator = iterator
        self.sc_iter = sc_iter
        self.sc_body = sc_body
        self.sc_else = sc_else
        super().__init__(*args, **kwargs)

    @cached_property
    def excs(self) -> ExcSet:
        return ExcSet(
            self.sc_iter.excs.remove(RtStopIteration).types |
            self.sc_body.excs.remove({RtContinue, RtBreak}).types |
            self.sc_else.excs.types
        )


class While(control_flow):
    _fields = ("condition", "sc_body", "sc_else")
    def __init__(self, condition: Any, sc_body: Scope, sc_else: Scope, *args, **kwargs):
        self.condition = condition
        self.sc_body = sc_body
        self.sc_else = sc_else
        super().__init__(*args, **kwargs)

    @cached_property
    def excs(self) -> ExcSet:
        return ExcSet(
            self.sc_body.excs.remove({RtContinue, RtBreak}).types |
            self.sc_else.excs.types
        )


class Call(control_flow):
    _fields = ("func",)
    def __init__(self, func: Any, *args, **kwargs):
        self.func = func
        super().__init__(*args, **kwargs)

    @cached_property
    def excs(self):
        from .context import Context
        if isinstance(self.func, Context) and self.func.finished:
            return self.func.excs
        # TODO 函数存在循环调用时获取函数真实异常集
        else:
            return ExcSet.ANY


class ExcHandle(AST):
    _fields = ("eg", "sc_handle")
    def __init__(self, eg: tuple[_TBaseRtExc], sc_handle: Scope):
        self.eg = eg
        self.sc_handle = sc_handle


class Try(control_flow):
    _fields = ("sc_try", "excepts", "sc_else", "sc_finally")
    def __init__(self, sc_try: Scope, excepts: list[ExcHandle], sc_else: Scope, sc_finally: Scope, *args, **kwargs):
        self.sc_try = sc_try
        self.excepts = excepts
        self.sc_else = sc_else
        self.sc_finally = sc_finally
        super().__init__(*args, **kwargs)

    @cached_property
    def excs(self) -> ExcSet:
        if self.sc_finally.excs.always:
            return self.sc_finally.excs
        else:
            excs = self.sc_try.excs
            handler_excs = set()
            for handler in self.excepts:
                excs = excs.remove_subclasses(handler.eg)
                for e in self.sc_try.excs.types:
                    if e is not None and issubclass(e, handler.eg):
                        # handler 将被启用，记录其异常
                        handler_excs.update(handler.sc_handle.excs.types)
                        break
            return ExcSet(
                excs.types |
                handler_excs |
                self.sc_else.excs.types |
                self.sc_finally.excs.types
            )


class Raise(control_flow):
    """
    所有流程中断操作均由 Raise 实现

    抛出 RtContinue, RtBreak, RtReturn 分别代替 continue, break, return，其余异常视为 raise

    exc 是异常实例。
    """
    _fields = ("exc",)
    def __init__(self, exc: RtBaseExc, *args, **kwargs):
        assert isinstance(exc, RtBaseExc)
        self.exc = exc
        super().__init__(*args, **kwargs)

    @property
    def excs(self) -> ExcSet:
        return ExcSet(self.exc)