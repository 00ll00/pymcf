from abc import abstractmethod, ABC
from contextlib import contextmanager
from contextvars import ContextVar
from numbers import Real
from typing import Self, overload, SupportsInt, Iterable

from pymcf.ast_ import Constructor, RtBaseVar, RtBaseIterator, Assign, Inplace, RtStopIteration, Compare
from pymcf.mcfunction import mcfunction
from pymcf.mc.commands import Resolvable, ScoreRef, EntityRef, ObjectiveRef, NameRef, NbtPath, NBTStorable, NbtRef, \
    RefWrapper, TextScoreComponent


class RtVar(RtBaseVar, ABC):
    ...


class NumberLike(ABC):

    @classmethod
    @abstractmethod
    def __create_var__(cls):
        ...

    def __add__(self, other):
        res = self.__create_var__()
        Assign(res, self)
        Inplace.Add(res, other)
        return res

    def __radd__(self, other):
        return self.__class__.__add__(other, self)

    def __sub__(self, other):
        res = self.__create_var__()
        Assign(res, self)
        Inplace.Sub(res, other)
        return res

    def __rsub__(self, other):
        return self.__class__.__sub__(other, self)

    def __mul__(self, other):
        res = self.__create_var__()
        Assign(res, self)
        Inplace.Mult(res, other)
        return res

    def __rmul__(self, other):
        return self.__class__.__mul__(other, self)

    def __floordiv__(self, other):
        res = self.__create_var__()
        Assign(res, self)
        Inplace.FloorDiv(res, other)
        return res

    def __rfloordiv__(self, other):
        return self.__class__.__floordiv__(other, self)

    def __truediv__(self, other):
        res = self.__create_var__()
        Assign(res, self)
        Inplace.Div(res, other)
        return res

    def __rtruediv__(self, other):
        return self.__class__.__truediv__(other, self)

    def __mod__(self, other):
        res = self.__create_var__()
        Assign(res, self)
        Inplace.Mod(res, other)
        return res

    def __rmod__(self, other):
        return self.__class__.__mod__(other, self)

    def __ne__(self, other):
        res = Bool.__create_var__()
        Compare.NotEq(res, self, other)
        return res

    def __lt__(self, other):
        res = Bool.__create_var__()
        Compare.Lt(res, self, other)
        return res

    def __le__(self, other):
        res = Bool.__create_var__()
        Compare.LtE(res, self, other)
        return res

    def __gt__(self, other):
        res = Bool.__create_var__()
        Compare.Gt(res, self, other)
        return res

    def __ge__(self, other):
        res = Bool.__create_var__()
        Compare.GtE(res, self, other)
        return res

    def __eq__(self, other):
        res = Bool.__create_var__()
        Compare.Eq(res, self, other)
        return res

    def __iadd__(self, other):
        Inplace.Add(self, other)
        return self

    def __isub__(self, other):
        Inplace.Sub(self, other)
        return self

    def __imul__(self, other):
        Inplace.Mult(self, other)
        return self

    def __ifloordiv__(self, other):
        Inplace.FloorDiv(self, other)
        return self

    def __itruediv__(self, other):
        Inplace.Div(self, other)
        return self

    def __imod__(self, other):
        Inplace.Mod(self, other)
        return self


class Entity(RefWrapper[EntityRef]):

    def __init__(self, ref: EntityRef):
        self.ref = ref

    @property
    def __metadata__(self) -> EntityRef:
        return self.ref


Name = NameRef


class ScoreBoard(RefWrapper[ObjectiveRef]):

    @overload
    def __init__(self, ref: ObjectiveRef): ...
    @overload
    def __init__(self, name: str): ...
    @overload
    def __init__(self, scb: Self): ...

    def __init__(self, arg):
        if isinstance(arg, ObjectiveRef):
            self.ref = arg
        elif isinstance(arg, str):
            self.ref = ObjectiveRef(name=arg)
        elif isinstance(arg, ScoreBoard):
            self.ref = arg.ref
        else:
            raise TypeError()

    @property
    def __metadata__(self) -> ObjectiveRef:
        return self.ref


type ScoreInitializer = NumberLike | SupportsInt | ScoreRef | None


class Score(RtVar, RefWrapper[ScoreRef], NumberLike):

    @property
    def __metadata__(self) -> ScoreRef:
        return ScoreRef(self.entity.__metadata__, self.objective.__metadata__)

    @overload
    def __init__(self, number: ScoreInitializer = None):
        ...

    @overload
    def __init__(self, target: EntityRef | str, objective: ObjectiveRef | str, number: NumberLike | Real = None):
        ...

    def __init__(self, *args):
        match len(args):
            case 0 | 1:
                ref = self._new_local_ref()
                self.entity = Entity(ref.target)
                self.objective = ScoreBoard(ref.objective)
                if len(args) == 1:
                    Assign(self, args[0])
            case 2 | 3:
                if isinstance(args[0], str):
                    target = NameRef(args[0])
                else:
                    target = args[0]
                if isinstance(args[1], str):
                    objective = ObjectiveRef(args[1])
                else:
                    objective = args[1]
                self.entity = Entity(target)
                self.objective = ScoreBoard(objective)
                if len(args) == 3:
                    Assign(self, args[2])
            case _:
                raise TypeError()

    @staticmethod
    def _new_local_ref() -> ScoreRef:
        return Constructor.current_constr().scope.new_local_score()

    @classmethod
    def __create_var__(cls) -> Self:
        return Score()

    def __assign__(self, value):
        Assign(target=self, value=value)

    def __repr__(self):
        return f"Score({self.__metadata__.resolve(None, None)})"

    def resolve(self, scope, fmt=None):
        if fmt is None:
            return super().resolve(scope, fmt)
        elif fmt == "json":
            return TextScoreComponent(self.__metadata__).resolve(scope, fmt)
        else:
            raise ValueError(f"unknown score format {fmt!r}.")

    def __bool_and__(self, other):
        res = Bool.__create_var__()
        Assign(res, self)
        Inplace.And(res, other)
        return res

    def __bool_or__(self, other):
        res = Bool.__create_var__()
        Assign(res, self)
        Inplace.Or(res, other)
        return res

    @mcfunction.inline
    def __pow__(self, power, modulo=None):
        if isinstance(power, RtBaseVar):
            res = Score(1)
            for _ in Range(power):
                res *= self
        else:
            power = int(power)
            if power < 0:
                raise ValueError()
            elif power == 0:
                return Score(1)
            res = Score(self)
            for _ in range(power - 1):
                res *= self
        return res

    @mcfunction.inline
    def __rpow__(self, other):
        return Score(other).__pow__(self)

Bool = Score


class Nbt(RefWrapper[NbtRef]):
    ...


class RtIterator[V: RtVar](RtVar, RtBaseIterator[V], ABC):
    ...


class RangeIterator(RtIterator[Score]):

    @overload
    def __init__(self, end: ScoreInitializer, /):
        ...

    @overload
    def __init__(self, start: ScoreInitializer, end: ScoreInitializer, step: ScoreInitializer = ..., /):
        ...

    def __init__(self, arg1, arg2=None, step=1, /):
        if arg2 is None:
            start = 0
            stop = arg1
        else:
            start = arg1
            stop = arg2
        self.start = Score(start)
        self.stop = int(stop) if isinstance(stop, SupportsInt) else Score(stop)
        self.step = int(step) if isinstance(step, SupportsInt) else Score(step)

    def __assign__(self, value):
        if not isinstance(value, RangeIterator):
            raise TypeError(f"不能将 {value.__class__.__name__} 赋值到 ScoreIterator")
        self.start.__assign__(value.start)
        if isinstance(value.stop, SupportsInt):
            self.stop = int(value.stop)
        else:
            self.stop = Score(value.stop)
        if isinstance(value.step, SupportsInt):
            self.step = int(value.step)
        else:
            self.step = Score(value.step)

    @classmethod
    def __create_var__(cls) -> Self:
        return RangeIterator(None, None, None)

    @mcfunction.inline
    def __next__(self) -> Score:
        if self.start < self.stop:
            self.start += self.step
            return self.start
        else:
            raise RtStopIteration()

    def __repr__(self):
        return f"RangeIterator({self.start!r}, {self.stop!r}, {self.step!r})"


class Range(RtVar, Iterable[Score]):

    @overload
    def __init__(self, end: ScoreInitializer, /):
        ...

    @overload
    def __init__(self, start: ScoreInitializer, end: ScoreInitializer, step: ScoreInitializer = ..., /):
        ...

    def __init__(self, arg1, arg2=None, step=1, /):
        if arg2 is None:
            start = 0
            stop = arg1
        else:
            start = arg1
            stop = arg2
        self.start = int(start) if isinstance(start, SupportsInt) else Score(start)
        self.stop = int(stop) if isinstance(stop, SupportsInt) else Score(stop)
        self.step = int(step) if isinstance(step, SupportsInt) else Score(step)

    def __assign__(self, value):
        if not isinstance(value, (Range, range)):
            raise TypeError(f"不能将 {value.__class__.__name__} 赋值到 Range")
        if isinstance(value.start, SupportsInt):
            self.start = int(value.start)
        else:
            self.start = Score(value.start)
        if isinstance(value.stop, SupportsInt):
            self.stop = int(value.stop)
        else:
            self.stop = Score(value.stop)
        if isinstance(value.step, SupportsInt):
            self.step = int(value.step)
        else:
            self.step = Score(value.step)

    @classmethod
    def __create_var__(cls) -> Self:
        return Range(None, None, None)

    def __iter__(self) -> RangeIterator:
        return RangeIterator(self.start, self.stop, self.step)

    def __contains__(self, item):
        """
        x in range
        """
        raise NotImplementedError()
