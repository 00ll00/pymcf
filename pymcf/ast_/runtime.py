from abc import abstractmethod, ABC, ABCMeta
from typing import final, Self, Iterator, Iterable


class _RtBaseExcMeta(ABCMeta):
    @property
    @abstractmethod
    def errno(cls) -> int:
        return cls._errno

    def __repr__(cls):
        return f"<{cls.__qualname__}(errno={cls.errno})>"

    def __int__(self) -> int:
        return self.errno

class RtBaseExc(BaseException, metaclass=_RtBaseExcMeta):
    _errno = NotImplemented  # TODO 异常代号范围化
    def __record__(self):
        from ._syntactic import Raise
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


class RtBaseData(ABC):

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
    def __create_tmp__(cls) -> Self:
        ...

class RtBaseIterator[V: RtBaseData](RtBaseData, Iterator, ABC):

    @final
    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self) -> V:
        """
        此方法构造迭代器的迭代流程，并且返回迭代对象
        """
