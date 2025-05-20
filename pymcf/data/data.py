from abc import abstractmethod, ABC
from contextlib import contextmanager
from contextvars import ContextVar
from numbers import Real
from typing import Self, overload

from pymcf.ast_ import Context, RtBaseData, RtBaseIterator, Assign, BinOp, Compare, AugAssign, RtStopIteration, BoolOp
from pymcf.mcfunction import mcfunction


class Identifier:

    @abstractmethod
    def __eq__(self, other):
        ...


class EntityIdentifier(Identifier, ABC):
    ...


class Name(EntityIdentifier):

    def __init__(self, name: str):
        self.name: str = name

    def __eq__(self, other: Self):
        return isinstance(other, Name) and self.name == other.name

    def __repr__(self):
        return self.name


class ScoreBoard(Identifier):

    def __init__(self, name: str):
        self.name: str = name

    def __eq__(self, other: Self):
        return isinstance(other, ScoreBoard) and self.name == other.name

    def __repr__(self):
        return self.name


class ScoreIdentifier(Identifier):

    def __init__(self, entity: EntityIdentifier, scb: ScoreBoard):
        self.entity: EntityIdentifier = entity
        self.scb: ScoreBoard = scb

    def __eq__(self, other: Self):
        return isinstance(other, ScoreIdentifier) and self.entity == other.entity and self.scb == other.scb

    def __repr__(self):
        return repr(f"{self.entity!r} {self.scb!r}")


_eq_identifier: ContextVar[bool] = ContextVar("eq_identifier", default=False)
"""
决定是否让 RtBaseData 实例的 __eq__ 函数直接使用其 identifier 的 __eq__
"""
# TODO 需要一个更好的实现方式


@contextmanager
def set_eq_identifier(b: bool):
    _o = _eq_identifier.get()
    try:
        _eq_identifier.set(b)
        yield
    finally:
        _eq_identifier.set(_o)


class RtData(RtBaseData):

    def __init__(self, identifier: Identifier):
        self.identifier: Identifier = identifier

    @abstractmethod
    def __assign__(self, value):
        """
        定义此类型如何赋值
        """


class NumberLike(ABC):

    @classmethod
    @abstractmethod
    def __create_tmp__(cls):
        ...

    def __add__(self, other):
        res = self.__create_tmp__()
        BinOp.Add(res, self, other)
        return res

    def __radd__(self, other):
        return self.__class__.__add__(other, self)

    def __sub__(self, other):
        res = self.__create_tmp__()
        BinOp.Sub(res, self, other)
        return res

    def __rsub__(self, other):
        return self.__class__.__sub__(other, self)

    def __mul__(self, other):
        res = self.__create_tmp__()
        BinOp.Mult(res, self, other)
        return res

    def __rmul__(self, other):
        return self.__class__.__mul__(other, self)

    def __floordiv__(self, other):
        res = self.__create_tmp__()
        BinOp.FloorDiv(res, self, other)
        return res

    def __rfloordiv__(self, other):
        return self.__class__.__floordiv__(other, self)

    def __truediv__(self, other):
        res = self.__create_tmp__()
        BinOp.Div(res, self, other)
        return res

    def __rtruediv__(self, other):
        return self.__class__.__truediv__(other, self)

    def __mod__(self, other):
        res = self.__create_tmp__()
        BinOp.Mod(res, self, other)
        return res

    def __rmod__(self, other):
        return self.__class__.__mod__(other, self)

    def __ne__(self, other):
        if _eq_identifier.get():
            return super().__ne__(other)
        else:
            res = Bool.__create_tmp__()
            Compare.NotEq(res, self, other)
            return res

    def __lt__(self, other):
        res = Bool.__create_tmp__()
        Compare.Lt(res, self, other)
        return res

    def __le__(self, other):
        res = Bool.__create_tmp__()
        Compare.LtE(res, self, other)
        return res

    def __gt__(self, other):
        res = Bool.__create_tmp__()
        Compare.Gt(res, self, other)
        return res

    def __ge__(self, other):
        res = Bool.__create_tmp__()
        Compare.GtE(res, self, other)
        return res

    def __eq__(self, other):
        if _eq_identifier.get():
            return super().__eq__(other)
        else:
            res = Bool.__create_tmp__()
            Compare.Eq(res, self, other)
            return res

    def __iadd__(self, other):
        AugAssign.Add(self, other)
        return self

    def __isub__(self, other):
        AugAssign.Sub(self, other)
        return self

    def __imul__(self, other):
        AugAssign.Mult(self, other)
        return self

    def __ifloordiv__(self, other):
        AugAssign.FloorDiv(self, other)
        return self

    def __itruediv__(self, other):
        AugAssign.Div(self, other)
        return self

    def __imod__(self, other):
        AugAssign.Mod(self, other)
        return self


type ScoreInitializer = NumberLike | Real | ScoreIdentifier | None


class Score(RtData, NumberLike):

    @overload
    def __init__(self): ...
    @overload
    def __init__(self, _: None): ...
    @overload
    def __init__(self, identifier: ScoreIdentifier): ...
    @overload
    def __init__(self, number: NumberLike, *, identifier: ScoreIdentifier=None): ...
    @overload
    def __init__(self, number: Real, *, identifier: ScoreIdentifier=None): ...
    @overload
    def __init__(self, entity: EntityIdentifier | str, scb: ScoreBoard | str): ...

    def __init__(self, *args, identifier: ScoreIdentifier = None):
        if len(args) == 0:
            identifier = self._new_tmp_identifier() if identifier is None else identifier
        elif len(args) == 1:
            arg = args[0]
            if arg is None:
                identifier = self._new_tmp_identifier()
            elif isinstance(arg, ScoreIdentifier):
                if identifier is None:
                    identifier = arg
                else:
                    raise ValueError("不能同时使用两个 identifier 初始化 Score")
            else:
                if identifier is None:
                    identifier = self._new_tmp_identifier()
                if isinstance(arg, NumberLike):
                    Assign(self, arg)
                elif isinstance(arg, Real):
                    Assign(self, int(arg))
                else:
                    raise ValueError(f"不能使用 {arg.__class__.__name__} 初始化 Score")
        elif len(args) == 2:
            if identifier is not None:
                raise ValueError("不能同时使用两个 identifier 初始化 Score")
            entity = EntityIdentifier(args[0])
            scb = ScoreBoard(args[1])
            identifier = ScoreIdentifier(entity, scb)

        super().__init__(identifier)

    @staticmethod
    def _new_tmp_identifier() -> ScoreIdentifier:
        return ScoreIdentifier(entity=Name(name=f"$tmp_{Context.current_ctx().new_tmp_id()}"), scb=ScoreBoard("$sys"))

    @classmethod
    def __create_tmp__(cls) -> Self:
        return Score(identifier=cls._new_tmp_identifier())

    def __assign__(self, value):
        Assign(target=self, value=value)

    def __repr__(self):
        return f"Score({self.identifier!r})"


Bool = Score


class RtIterator[V: RtData](RtBaseIterator[V], ABC):
    ...


class ScoreRange(RtIterator[Score]):

    @overload
    def __init__(self, end: ScoreInitializer, /): ...

    @overload
    def __init__(self, start: ScoreInitializer, end: ScoreInitializer, step: ScoreInitializer = ..., /): ...

    def __init__(self, arg1, arg2=None, step=1):
        if arg2 is None:
            start = 0
            end = arg1
        else:
            start = arg1
            end = arg2
        self.i = Score(start)
        self.end = int(end) if isinstance(end, Real) else Score(end)
        self.step = int(step) if isinstance(end, Real) else Score(step)

    def __assign__(self, value):
        if not isinstance(value, ScoreRange):
            raise TypeError(f"不能将 {value.__class__.__name__} 赋值到 ScoreRange")
        self.i.__assign__(value.i)
        if isinstance(value.end, Real):
            self.end = int(value.end)
        else:
            self.end = Score(value.end)
        if isinstance(value.step, Real):
            self.step = int(value.step)
        else:
            self.step = Score(value.step)

    @classmethod
    def __create_tmp__(cls) -> Self:
        return ScoreRange(None, None, None)

    @mcfunction.inline
    def __next__(self) -> Score:
        if self.i < self.end:
            self.i += self.step
            return self.i
        else:
            raise RtStopIteration()

    def __repr__(self):
        return f"ScoreRange({self.i!r}, {self.end!r}, {self.step!r})"

# TODO nbt定义
# class NbtIdentifier(Identifier):
#     def __init__(self):
#         ...
#
#
# class Nbt(RtData, ABC):
#     def __init__(self, identifier: NbtIdentifier):
#         super().__init__(identifier)
#
#
# class NbtInt(Nbt, NumberLike):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
