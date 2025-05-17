from abc import ABC, abstractmethod, ABCMeta
from ast import AST as _AST, unaryop, UAdd, USub, Not, Invert, boolop, And, Or, operator, Add, Sub, Mult, Div, FloorDiv, Mod, \
    Pow, LShift, RShift, BitOr, BitXor, BitAnd, MatMult, cmpop, Eq, NotEq, Lt, LtE, Gt, GtE, Is, IsNot, In, NotIn
from functools import reduce, cached_property
from typing import Any, Self, Iterable, final


class _RtBaseExcMeta(ABCMeta):
    @property
    @abstractmethod
    def errno(cls) -> int:
        return cls._errno

    def __repr__(cls):
        return f"<{cls.__qualname__}(errno={cls.errno})>"


class RtBaseExc(BaseException, metaclass=_RtBaseExcMeta):
    _errno = NotImplemented  # TODO 异常代号范围化
    def __record__(self):
        Raise(exc=self)


class RtSysExc(RtBaseExc):
    """
    系统保留的异常
    """


class _RtNormalExcMeta(_RtBaseExcMeta, ABC):

    def __subclasscheck__(self, subclass):
        if subclass is RtAnyNormalExc:
            return True
        return type.__subclasscheck__(self, subclass)


class RtNormalExc(RtBaseExc, metaclass=_RtNormalExcMeta):
    """
    允许用户定义的异常

    通过继承此类构造新的运行期异常
    """


class RtCfExc(RtSysExc, ABC):
    """
    流程控制异常
    """


@final
class RtUnreachable(RtCfExc):
    """
    RtUnreachable 用于终止不可达代码的生成
    """
    _errno = -42
    def __init_subclass__(cls, **kwargs):
        raise TypeError(f'RtUnreachable cannot be inherited')
    def __init__(self):
        ...
    def __record__(self):
        ...  # raise RtUnreachable 不需要被记录


@final
class RtAnyNormalExc(RtNormalExc):
    """
    RtAnyNormalExc 是所有 RtNormalExc 子类的子类，仅用于抛出异常不明确时作为*任意*异常可能被抛出的提示

    不可继承，不可实例化
    """
    _errno = -42
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtAnyNormalExc' is not an acceptable base type")

    def __init__(self):
        raise TypeError("type 'RtAnyNormalExc' cannot be instantiated")


@final
class RtStopIteration(RtNormalExc):
    _errno = -1
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtStopIteration' is not an acceptable base type")


@final
class RtContinue(RtCfExc):
    _errno = -2
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtContinue' is not an acceptable base type")


@final
class RtBreak(RtCfExc):
    _errno = -3
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtBreak' is not an acceptable base type")


@final
class RtReturn(RtCfExc):
    _errno = -4
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtReturn' is not an acceptable base type")
    def __init__(self, value):
        self.value = value


type _TBaseRtExc = type[RtBaseExc]


class ExcSet:
    """
    异常集合

    不可变集合，要修改内容需要创建新集合
    """

    EMPTY: Self
    """
    空异常集合，不含任何异常。
    """

    ANY: Self
    """
    满异常集合，可能出现任意 RtNormalExc 或无异常。用于描述异常未知的函数。
    """

    def __init__(self, exc: _TBaseRtExc | Iterable[_TBaseRtExc] | Self | None):
        self._set: set[_TBaseRtExc | None] = set()
        if isinstance(exc, type):
            self._set.add(exc)
        elif isinstance(exc, RtBaseExc):
            self._set.add(type(exc))
        elif isinstance(exc, ExcSet):
            self._set.update(exc._set)
        elif exc is None:
            self._set.add(exc)
        else:
            try:
                self._set.update(exc)
            except:
                raise ValueError(f'无效的初始化值: {exc!r}')

        if len(self._set) == 0:
            self._set.add(None)

        self._always = None not in self._set
        self._might = len(self._set - {None}) > 0

    def remove(self, exc: _TBaseRtExc | set[_TBaseRtExc]) -> Self:
        if isinstance(exc, type):
            exc = {exc}
        assert RtAnyNormalExc not in exc
        return ExcSet(self._set - exc)

    def remove_subclasses(self, exc: _TBaseRtExc| Iterable[_TBaseRtExc]) -> Self:
        if isinstance(exc, type):
            exc = (exc, )
        else:
            exc = tuple(exc)
        res = ExcSet(e for e in self._set if e is None or not issubclass(e, exc))
        has_any = RtAnyNormalExc in self._set and not issubclass(RtNormalExc, exc)  # 如果被移除的类包含 RtNormalExc 的基类，则可以移除 RtAnyNormalExc
        if not has_any:
            res = ExcSet(res._set - {RtAnyNormalExc})
        return res

    @property
    def set(self) -> set[_TBaseRtExc | None]:
        return self._set.copy()
    @property
    def always(self) -> bool:
        return self._always
    @property
    def might(self) -> bool:
        return self._might


ExcSet.EMPTY = ExcSet(None)
ExcSet.ANY = ExcSet({None, RtAnyNormalExc})


class AST(_AST):
    def clear_cache(self): ...


class stmt(AST):

    @property
    @abstractmethod
    def excs(self) -> ExcSet:
        ...

    def clear_cache(self):
        self._cache.clear()

    def __init__(self, *_, _offline: bool = None, **__):
        self._cache = {}
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
        self._excs: ExcSet = None

    @property
    def excs(self) -> ExcSet:
        if self._excs is not None:
            return self._excs
        if self.flow:
            s = reduce(lambda a, b: a | b, (st.excs.set for st in self.flow), set())
            if self.flow[-1].excs.always:
                s.discard(None)  # 若 flow 最后一个语句一定引发异常，则整个 scope 必然引发异常
            self._excs = ExcSet(s)
        else:
            self._excs = ExcSet.EMPTY
        return self._excs

    def clear_cache(self):
        self._excs = None


class compiler_hint(stmt, ABC):
    """
    compiler_hint 用于提示编译器调整编译策略
    """
    excs = ExcSet.EMPTY


class operation(stmt, ABC):
    """
    operation 不会改变控制流，也不包含控制流
    """
    excs = ExcSet.EMPTY


class control_flow(stmt, ABC):
    """
    control_flow 实现控制流语句
    """


class Raw(operation):
    _fields = ("code",)
    def __init__(self, code: str, *args, **kwargs):
        self.code = code
        super().__init__(*args, **kwargs)


class Assign(operation):
    _fields = ("target", "value")
    def __init__(self, target, value, *args, **kwargs):
        self.target = target
        self.value = value
        super().__init__(*args, **kwargs)


class UnaryOp(operation):
    _fields = ("op", "value")
    def __init__(self, op: unaryop, value, *args, **kwargs):
        self.op = op
        self.value = value
        super().__init__(*args, **kwargs)

    @staticmethod
    def UAdd(value, *args, **kwargs):
        return UnaryOp(UAdd(), value, *args, **kwargs)

    @staticmethod
    def USub(value, *args, **kwargs):
        return UnaryOp(USub(), value, *args, **kwargs)

    @staticmethod
    def Not(value, *args, **kwargs):
        return UnaryOp(Not(), value, *args, **kwargs)

    @staticmethod
    def Invert(value, *args, **kwargs):
        return UnaryOp(Invert(), value, *args, **kwargs)


class BoolOp(operation):
    _fields = ("op", "target", "left", "right")
    def __init__(self, op: boolop, target, left, right, *args, **kwargs):
        self.op = op
        self.target = target
        self.left = left
        self.right = right
        super().__init__(*args, **kwargs)

    @staticmethod
    def And(target, left, right, *args, **kwargs):
        return BoolOp(And(), target, left, right, *args, **kwargs)

    @staticmethod
    def Or(target, left, right, *args, **kwargs):
        return BoolOp(Or(), target, left, right, *args, **kwargs)

class BinOp(operation):
    _fields = ("op", "target", "left", "right")
    def __init__(self, op: operator, target, left, right, *args, **kwargs):
        self.op = op
        self.target = target
        self.left = left
        self.right = right
        super().__init__(*args, **kwargs)

    @staticmethod
    def Add(target, left, right, *args, **kwargs):
        return BinOp(Add(), target, left, right, *args, **kwargs)

    @staticmethod
    def Sub(target, left, right, *args, **kwargs):
        return BinOp(Sub(), target, left, right, *args, **kwargs)

    @staticmethod
    def Mult(target, left, right, *args, **kwargs):
        return BinOp(Mult(), target, left, right, *args, **kwargs)

    @staticmethod
    def Div(target, left, right, *args, **kwargs):
        return BinOp(Div(), target, left, right, *args, **kwargs)

    @staticmethod
    def FloorDiv(target, left, right, *args, **kwargs):
        return BinOp(FloorDiv(), target, left, right, *args, **kwargs)

    @staticmethod
    def Mod(target, left, right, *args, **kwargs):
        return BinOp(Mod(), target, left, right, *args, **kwargs)

    @staticmethod
    def Pow(target, left, right, *args, **kwargs):
        return BinOp(Pow(), target, left, right, *args, **kwargs)

    @staticmethod
    def LShift(target, left, right, *args, **kwargs):
        return BinOp(LShift(), target, left, right, *args, **kwargs)

    @staticmethod
    def RShift(target, left, right, *args, **kwargs):
        return BinOp(RShift(), target, left, right, *args, **kwargs)

    @staticmethod
    def BitOr(target, left, right, *args, **kwargs):
        return BinOp(BitOr(), target, left, right, *args, **kwargs)

    @staticmethod
    def BitXor(target, left, right, *args, **kwargs):
        return BinOp(BitXor(), target, left, right, *args, **kwargs)

    @staticmethod
    def BitAnd(target, left, right, *args, **kwargs):
        return BinOp(BitAnd(), target, left, right, *args, **kwargs)

    @staticmethod
    def MatMult(target, left, right, *args, **kwargs):
        return BinOp(MatMult(), target, left, right, *args, **kwargs)


class AugAssign(operation):
    _fields = ("op", "target", "value")
    def __init__(self, op: operator, target, value, *args, **kwargs):
        self.op = op
        self.target = target
        self.value = value
        super().__init__(*args, **kwargs)

    @staticmethod
    def Add(target, value, *args, **kwargs):
        return AugAssign(Add(), target, value, *args, **kwargs)

    @staticmethod
    def Sub(target, value, *args, **kwargs):
        return AugAssign(Sub(), target, value, *args, **kwargs)

    @staticmethod
    def Mult(target, value, *args, **kwargs):
        return AugAssign(Mult(), target, value, *args, **kwargs)

    @staticmethod
    def Div(target, value, *args, **kwargs):
        return AugAssign(Div(), target, value, *args, **kwargs)

    @staticmethod
    def FloorDiv(target, value, *args, **kwargs):
        return AugAssign(FloorDiv(), target, value, *args, **kwargs)

    @staticmethod
    def Mod(target, value, *args, **kwargs):
        return AugAssign(Mod(), target, value, *args, **kwargs)

    @staticmethod
    def Pow(target, value, *args, **kwargs):
        return AugAssign(Pow(), target, value, *args, **kwargs)

    @staticmethod
    def LShift(target, value, *args, **kwargs):
        return AugAssign(LShift(), target, value, *args, **kwargs)

    @staticmethod
    def RShift(target, value, *args, **kwargs):
        return AugAssign(RShift(), target, value, *args, **kwargs)

    @staticmethod
    def BitOr(target, value, *args, **kwargs):
        return AugAssign(BitOr(), target, value, *args, **kwargs)

    @staticmethod
    def BitXor(target, value, *args, **kwargs):
        return AugAssign(BitXor(), target, value, *args, **kwargs)

    @staticmethod
    def BitAnd(target, value, *args, **kwargs):
        return AugAssign(BitAnd(), target, value, *args, **kwargs)

    @staticmethod
    def MatMult(target, value, *args, **kwargs):
        return AugAssign(MatMult(), target, value, *args, **kwargs)


class Compare(operation):
    _fields = ("op", "target", "left", "right")
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

    @staticmethod
    def Is(target, left, right, *args, **kwargs):
        return Compare(Is(), target, left, right, *args, **kwargs)

    @staticmethod
    def IsNot(target, left, right, *args, **kwargs):
        return Compare(IsNot(), target, left, right, *args, **kwargs)

    @staticmethod
    def In(target, left, right, *args, **kwargs):
        return Compare(In(), target, left, right, *args, **kwargs)

    @staticmethod
    def NotIn(target, left, right, *args, **kwargs):
        return Compare(NotIn(), target, left, right, *args, **kwargs)


class If(control_flow):
    _fields = ("condition", "sc_body", "sc_else")
    def __init__(self, condition: Any, sc_body: Scope, sc_else: Scope, *args, **kwargs):
        self.condition = condition
        self.sc_body = sc_body
        self.sc_else = sc_else
        super().__init__(*args, **kwargs)

    @property
    def excs(self) -> ExcSet:
        if "excs" not in self._cache:
            self._cache["excs"] = ExcSet(self.sc_body.excs.set | self.sc_else.excs.set)
        return self._cache["excs"]


class For(control_flow):
    _fields = ("iterator", "sc_iter", "sc_body", "sc_else")
    def __init__(self, iterator: Any, sc_iter: Scope, sc_body: Scope, sc_else: Scope, *args, **kwargs):
        self.iterator = iterator
        self.sc_iter = sc_iter
        self.sc_body = sc_body
        self.sc_else = sc_else
        super().__init__(*args, **kwargs)

    @property
    def excs(self) -> ExcSet:
        if "excs" not in self._cache:
            self._cache["excs"] = ExcSet(
                self.sc_iter.excs.remove(RtStopIteration).set |
                self.sc_body.excs.remove({RtContinue, RtBreak}).set |
                self.sc_else.excs.set
            )
        return self._cache["excs"]


class While(control_flow):
    _fields = ("condition", "sc_body", "sc_else")
    def __init__(self, condition: Any, sc_body: Scope, sc_else: Scope, *args, **kwargs):
        self.condition = condition
        self.sc_body = sc_body
        self.sc_else = sc_else
        super().__init__(*args, **kwargs)

    @property
    def excs(self) -> ExcSet:
        if "excs" not in self._cache:
            self._cache["excs"] = ExcSet(
                self.sc_body.excs.remove({RtContinue, RtBreak}).set |
                self.sc_else.excs.set
            )
        return self._cache["excs"]


class Call(control_flow):
    _fields = ("func",)
    def __init__(self, func: Any, *args, **kwargs):
        self.func = func
        super().__init__(*args, **kwargs)

    @property
    def excs(self):
        if "excs" not in self._cache:
            from .context import Context
            if isinstance(self.func, Context) and self.func.finished:
                self._cache["excs"] = self.func.excs
            # TODO 函数存在循环调用时获取函数真实异常集
            else:
                self._cache["excs"] = ExcSet.ANY
        return self._cache["excs"]


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

    @property
    def excs(self) -> ExcSet:
        if "excs" not in self._cache:
            if self.sc_finally.excs.always:
                self._cache["excs"] = self.sc_finally.excs
            else:
                excs = self.sc_try.excs
                handler_excs = []
                for handler in self.excepts:
                    excs = excs.remove_subclasses(handler.eg)
                    for e in excs.set:
                        if e is not None and issubclass(e, handler.eg):
                            # handler 将被启用，记录其异常
                            handler_excs.append(handler.sc_handle.excs.set)
                            break
                self._cache["excs"] = ExcSet(
                    excs.set |
                    reduce(lambda a, b: a | b, handler_excs, set()) |
                    self.sc_else.excs.set |
                    self.sc_finally.excs.set
                )
        return self._cache["excs"]


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
        return ExcSet(self.exc_class)

    @property
    def exc_class(self) -> _TBaseRtExc:
        return type(self.exc)