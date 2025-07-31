import functools
from abc import abstractmethod, ABC
from numbers import Real
from typing import Self, overload, SupportsInt, Iterable

from pymcf.ast_ import Constructor, RtBaseVar, RtBaseIterator, Assign, Inplace, RtStopIteration, Compare, Raw, \
    UnaryOp
from pymcf.mc.commands import ScoreRef, EntityRef, ObjectiveRef, NameRef, NbtPath, NbtStorable, NbtRef, \
    RefWrapper, TextScoreComponent, TextComponent, ScoreboardAdd, AtE, \
    Selector, Storage, TextNBTComponent
from pymcf.mcfunction import mcfunction
from .nbtlib import *


class maybe_classmethod:

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        if instance is None:
            @functools.wraps(self.func)
            def wrapper(*args, **kwargs):
                return self.func(owner, *args, **kwargs)
        else:
            @functools.wraps(self.func)
            def wrapper(*args, **kwargs):
                return self.func(instance, *args, **kwargs)
        return wrapper


class RtVar(RtBaseVar, ABC):
    ...


class NumberLike(ABC):

    @classmethod
    @abstractmethod
    def __create_var__(cls):
        ...

    def __add__(self, other, _rev=False):
        res = other.__create_var__() if _rev else self.__create_var__()
        Assign(res, self)
        Inplace.Add(res, other)
        return res

    def __radd__(self, other):
        return self.__class__.__add__(other, self, _rev=True)

    def __sub__(self, other, _rev=False):
        res = other.__create_var__() if _rev else self.__create_var__()
        Assign(res, self)
        Inplace.Sub(res, other)
        return res

    def __rsub__(self, other):
        return self.__class__.__sub__(other, self, _rev=True)

    def __mul__(self, other, _rev=False):
        res = other.__create_var__() if _rev else self.__create_var__()
        Assign(res, self)
        Inplace.Mult(res, other)
        return res

    def __rmul__(self, other):
        return self.__class__.__mul__(other, self, _rev=True)

    def __floordiv__(self, other, _rev=False):
        res = other.__create_var__() if _rev else self.__create_var__()
        Assign(res, self)
        Inplace.FloorDiv(res, other)
        return res

    def __rfloordiv__(self, other):
        return self.__class__.__floordiv__(other, self, _rev=True)

    def __truediv__(self, other, _rev=False):
        res = other.__create_var__() if _rev else self.__create_var__()
        Assign(res, self)
        Inplace.Div(res, other)
        return res

    def __rtruediv__(self, other):
        return self.__class__.__truediv__(other, self, _rev=True)

    def __mod__(self, other, _rev=False):
        res = other.__create_var__() if _rev else self.__create_var__()
        Assign(res, self)
        Inplace.Mod(res, other)
        return res

    def __rmod__(self, other):
        return self.__class__.__mod__(other, self, _rev=True)

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

    def __pos__(self):
        res = self.__create_var__()
        res.__assign__(self)
        return res

    def __neg__(self):
        res = self.__create_var__()
        res.__assign__(0)
        res.__isub__(self)
        return res


class BoolLike:

    def __bool_and__(self, other):
        res = Bool.__create_var__()
        res.__assign__(self)
        Inplace.And(res, other)
        return res

    def __bool_or__(self, other):
        res = Bool.__create_var__()
        res.__assign__(self)
        Inplace.Or(res, other)
        return res

    def __bool_not__(self):
        res = Bool.__create_var__()
        UnaryOp.Not(res, self)
        return res


class Entity(RefWrapper[EntityRef]):

    __base_selector__ = AtE()

    def __new__(cls, *args, _ref=None, **kwargs):
        self = super().__new__(cls)
        if _ref is not None:
            self.ref = _ref
        return self

    @overload
    def __init__(self, entity: Self): ...
    @overload
    def __init__(self, ref: EntityRef): ...

    def __init__(self, arg1):
        if isinstance(arg1, EntityRef):
            self.ref = arg1
        elif isinstance(arg1, Entity):
            self.ref = arg1.ref
        else:
            raise TypeError()

    @property
    def __metadata__(self) -> EntityRef:
        return self.ref

    @classmethod
    @overload
    def select[E: Entity](cls: type[E], selector: Selector = None, /, **kwargs) -> E:
        ...

    @overload
    def select[E: Entity](self: E, selector: Selector = None, /, **kwargs) -> E:
        ...

    @maybe_classmethod
    def select(self_or_cls, selector: Selector = None, /, **kwargs):
        if isinstance(self_or_cls, type):
            base = self_or_cls.__base_selector__
            cls = self_or_cls
        else:
            assert isinstance(self_or_cls.ref, Selector)
            base = self_or_cls.ref
            cls = type(self_or_cls)
        if selector is None:
            return cls.__new__(cls, _ref=base.merge(kwargs))
        else:
            return cls.__new__(cls, _ref=selector.merge(base))

    def __repr__(self):
        return f"{self.__class__.__name__}@{self.__metadata__.__class__.__name__}({self.__metadata__.__dict__})"

class ScoreBoard(RefWrapper[ObjectiveRef]):

    @overload
    def __init__(self, ref: ObjectiveRef): ...
    @overload
    def __init__(self, name: str, criteria: str = "dummy", display_name: str | TextComponent = None): ...
    @overload
    def __init__(self, scb: Self): ...

    def __init__(self, *args):
        if len(args) == 1:
            if isinstance(args[0], ObjectiveRef):
                self.ref = args[0]
            elif isinstance(args[0], ScoreBoard):
                self.ref = args[0].ref
            elif isinstance(args[0], str):
                self.__init__(args[0], "dummy", None)
            else:
                raise TypeError()
        elif len(args) == 2:
            self.__init__(args[0], args[1], None)
        elif len(args) == 3:
            name, criteria, display_name = args
            self.try_add_new_scb(name, criteria, display_name)
            self.ref = ObjectiveRef(name=name)
        else:
            raise TypeError()

    def __repr__(self):
        return f"ScoreBoard({self.__metadata__.objective})"

    @staticmethod
    def try_add_new_scb(name, criteria, display_name):
        from pymcf.project import Project
        prj = Project.instance()
        if name in prj.scb_rec:
            assert criteria == prj.scb_rec[name][0]
        else:
            prj.scb_rec[name] = (criteria, display_name)
            with prj.scb_init_constr:
                Raw(ScoreboardAdd(ObjectiveRef(name=name), criteria, display_name))

    @property
    def __metadata__(self) -> ObjectiveRef:
        return self.ref


type ScoreInitializer = NumberLike | SupportsInt | ScoreRef | None


class Score(BoolLike, RtVar, RefWrapper[ScoreRef], NumberLike):

    @property
    def __metadata__(self) -> ScoreRef:
        return ScoreRef(self.target.__metadata__, self.objective.__metadata__)

    @overload
    def __init__(self, number: ScoreInitializer = None):
        ...

    @overload
    def __init__(self, target: Entity | EntityRef | str, objective: ScoreBoard | ObjectiveRef | str, number: NumberLike | Real = None):
        ...

    def __init__(self, *args):
        self.target: Entity
        self.objective: ScoreBoard
        match len(args):
            case 0 | 1:
                ref = self._new_local_ref()
                self.target = Entity(ref.target)
                self.objective = ScoreBoard(ref.objective)
                if len(args) == 1:
                    Assign(self, args[0])
            case 2 | 3:
                self.target = Entity(args[0]) if not isinstance(args[0], str) else Entity(NameRef(args[0]))
                self.objective = ScoreBoard(args[1])
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
        return f"Score({self.target!r}, {self.objective!r})"

    def __format__(self, format_spec):
        match format_spec:
            case "":
                return self
            case "json":
                return TextScoreComponent(self.__metadata__)
            case _:
                raise SyntaxError(f"unsupported format specification: {format_spec}")

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

type _T_NbtData = type[NbtData | NbtCompoundSchema]

class Nbt(RtVar, RefWrapper[NbtRef]):

    @property
    def __metadata__(self) -> NbtRef:
        return NbtRef(self.target, self.path)

    @overload
    def __init__(self, data: NbtData | None = None, shema: _T_NbtData = None):
        ...

    @overload
    def __init__(self, target: NbtStorable | EntityRef | Entity | str, path: NbtPath | str, data: NbtData | None = None, shema: _T_NbtData = None):
        ...

    def __init__(self, *args, shema: _T_NbtData = None):
        self.shema: _T_NbtData = shema
        match len(args):
            case 0 | 1:
                ref = self._new_local_ref()
                self.target = ref.target
                self.path = ref.path
                if len(args) == 1:
                    Assign(self, args[0])
            case 2 | 3:
                target = args[0]
                path = args[1]
                if isinstance(target, NbtStorable):
                    self.target = target
                elif isinstance(target, EntityRef):
                    self.target = target.ref
                elif isinstance(target, Entity):
                    self.target = target.__metadata__.ref
                else:
                    self.target = Storage(str(target))
                self.path = path if isinstance(path, NbtPath) else NbtPath(path)
                if len(args) == 3:
                    Assign(self, args[2])
            case _:
                raise TypeError()

    @classmethod
    def __create_var__(cls) -> Self:
        return Nbt()

    def __assign__(self, value):
        Assign(target=self, value=value)

    def __repr__(self):
        return f"Nbt({self.target!r}, {self.path!r})"

    def __format__(self, format_spec):
        match format_spec:
            case "":
                return self
            case "json":
                return TextNBTComponent(self.__metadata__)
            case _:
                raise SyntaxError(f"unsupported format specification: {format_spec}")

    @staticmethod
    def _new_local_ref() -> NbtRef:
        return Constructor.current_constr().scope.new_local_nbt()

    def __eq__(self, other):
        raise NotImplementedError()


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
            curr = Score(self.start)
            self.start += self.step
            return curr
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
