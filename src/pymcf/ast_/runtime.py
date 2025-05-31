import math
from abc import abstractmethod, ABC, ABCMeta
from typing import final, Self, Iterator, Iterable, SupportsInt


class _RtBaseExcMeta(ABCMeta):
    @property
    def errno_range(cls) -> tuple[int, int]:
        assert cls._errno_range is not NotImplemented
        if isinstance(cls._errno_range, int):
            return (cls._errno_range, cls._errno_range)
        return cls._errno_range

    def __repr__(cls):
        return f"<{cls.__qualname__} {cls._errno_range}>"


class RtBaseExc(BaseException, metaclass=_RtBaseExcMeta):
    _errno_range = (-math.inf, math.inf)
    _errno = NotImplemented
    def __init__(self):
        raise TypeError(f"type {self.__class__.__name__} cannot be instantiated")
    def __record__(self):
        from ._syntactic import Raise
        self.__traceback__ = None  # 释放 __traceback__，减少内存占用 TODO 记录有用的 traceback 信息
        Raise(exc=self)

    def __int__(self):
        return self.errno

    @property
    def errno(self):
        return self._errno

class RtSysExc(RtBaseExc):
    """
    系统保留的异常
    """
    _errno_range = (-math.inf, -1)
    def __init__(self):
        raise TypeError(f"type {self.__class__.__name__} cannot be instantiated")

class _RtNormalExcMeta(_RtBaseExcMeta):

    def __subclasscheck__(self, subclass):
        if subclass is RtAnyNormalExc:
            return True
        return type.__subclasscheck__(self, subclass)


class RtNormalExc(RtBaseExc, metaclass=_RtNormalExcMeta):
    """
    允许用户定义的异常

    通过继承此类构造新的运行期异常
    """
    _errno_range = (1, math.inf)


class RtCfExc(RtSysExc, ABC):
    """
    流程控制异常
    """
    _errno_range = (-4, -2)

@final
class RtUnreachable(RtCfExc):
    """
    RtUnreachable 用于终止不可达代码的生成
    """
    _errno_range = -42
    _errno = -42
    def __init_subclass__(cls, **kwargs):
        raise TypeError(f'RtUnreachable cannot be inherited')
    def __init__(self):
        pass
    def __record__(self):
        ...  # raise RtUnreachable 不需要被记录


@final
class RtAnyNormalExc(RtNormalExc):
    """
    RtAnyNormalExc 是所有 RtNormalExc 子类的子类，仅用于抛出异常不明确时作为*任意*异常可能被抛出的提示

    不可继承，不可实例化
    """
    _errno_range = (1, math.inf)
    def __init_subclass__(cls, **kwargs):
        raise TypeError(f"type 'RtAnyNormalExc' is not an acceptable base type")


@final
class RtStopIteration(RtNormalExc):
    _errno_range = -1
    _errno = -1
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtStopIteration' is not an acceptable base type")
    def __init__(self):
        pass


@final
class RtContinue(RtCfExc):
    _errno_range = -2
    _errno = -2
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtContinue' is not an acceptable base type")
    def __init__(self):
        pass


@final
class RtBreak(RtCfExc):
    _errno_range = -3
    _errno = -3
    def __init_subclass__(cls, **kwargs):
        raise TypeError("type 'RtBreak' is not an acceptable base type")
    def __init__(self):
        pass


@final
class RtReturn(RtCfExc):
    _errno_range = -4
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
        self._types: set[_TBaseRtExc | None] = set()
        if isinstance(exc, type):
            self._types.add(exc)
        elif isinstance(exc, RtBaseExc):
            self._types.add(type(exc))
        elif isinstance(exc, ExcSet):
            self._types.update(exc._types)
        elif exc is None:
            self._types.add(exc)
        else:
            try:
                self._types.update(exc)
            except:
                raise ValueError(f'无效的初始化值: {exc!r}')

        if len(self._types) == 0:
            self._types.add(None)

        self._always = None not in self._types
        self._might = len(self._types - {None}) > 0

    def remove(self, exc: _TBaseRtExc | set[_TBaseRtExc]) -> Self:
        if isinstance(exc, type):
            exc = {exc}
        assert RtAnyNormalExc not in exc
        return ExcSet(self._types - exc)

    def remove_subclasses(self, exc: _TBaseRtExc| Iterable[_TBaseRtExc]) -> Self:
        if isinstance(exc, type):
            exc = (exc, )
        else:
            exc = tuple(exc)
        res = ExcSet(e for e in self._types if e is None or not issubclass(e, exc))
        has_any = RtAnyNormalExc in self._types and not issubclass(RtNormalExc, exc)  # 如果被移除的类包含 RtNormalExc 的基类，则可以移除 RtAnyNormalExc
        if not has_any:
            res = ExcSet(res._types - {RtAnyNormalExc})
        return res

    @property
    def types(self) -> set[_TBaseRtExc | None]:
        return self._types.copy()
    @property
    def always(self) -> bool:
        return self._always
    @property
    def might(self) -> bool:
        return self._might


ExcSet.EMPTY = ExcSet(None)
ExcSet.ANY = ExcSet({None, RtAnyNormalExc})


class RtBaseVar(ABC):

    def __bool_and__(self, other):
        """
        覆盖此方法以重写 and 运算
        """
        return NotImplemented

    def __bool_or__(self, other):
        """
        覆盖此方法以重写 or 运算
        """
        return NotImplemented

    @abstractmethod
    def __assign__(self, value):
        """
        实现此方法定义运行期数据赋值操作
        """

    @classmethod
    @abstractmethod
    def __create_var__(cls) -> Self:
        ...

class RtBaseIterator[V: RtBaseVar](Iterator[V], ABC):

    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self) -> V:
        """
        此方法构造迭代器的迭代流程，并且返回迭代对象
        """


class RtIterable[V: RtBaseVar](Iterable[V], ABC):

    @abstractmethod
    def __iter__(self) -> RtBaseIterator[V]:
        ...


class RtCtxManager(ABC):

    @abstractmethod
    def __enter__(self): ...

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback): ...
