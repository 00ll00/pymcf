from abc import ABC
from collections import defaultdict
from typing import Optional, Any, Dict

from pymcf._frontend.context import MCFContext
from pymcf.data.data import InGameData
from pymcf.jsontext import IJsonText, JsonText, JsonTextComponent
from pymcf.operations import raw, ScoreSetValueOp, ScoreCopyOp, ScoreLTScoreOp, ScoreResetValueOp, \
    ScoreLTValueOp, ScoreLEScoreOp, ScoreLEValueOp, ScoreGTScoreOp, ScoreGTValueOp, ScoreGEScoreOp, ScoreGEValueOp, \
    ScoreEQScoreOp, ScoreEQValueOp, ScoreAddValueOp, ScoreAddScoreOp, ScoreSubValueOp, ScoreSubScoreOp, ScoreMulScoreOp, \
    ScoreDivScoreOp, ScoreModScoreOp, DefScoreBoardOp, ScoreNEScoreOp, ScoreNEValueOp
from pymcf.util import staticproperty, lazy


class Scoreboard:
    _dummy_count = 0

    _all: Dict[str, "Scoreboard"] = {}

    def __new__(cls, name: str, scb_type: str = None, display: JsonText = None):
        if name in Scoreboard._all:
            self = Scoreboard._all[name]
            if scb_type is not None:
                assert self.type == scb_type
            return self

        else:
            self = super().__new__(cls)
            Scoreboard._all[name] = self

        if not MCFContext.in_context:
            with MCFContext.INIT_STORE:
                DefScoreBoardOp(name, scb_type, JsonText.convert_from(display))
        else:
            DefScoreBoardOp(name, scb_type, JsonText.convert_from(display))

        return self

    def __init__(self, name: str, scb_type: str = None, display: JsonText | Any = None):
        self.name = name
        self.type = scb_type if scb_type is not None else "dummy"
        self.display = JsonText.convert_from(display)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.name} {self.type}"

    @staticmethod
    def new_dummy():
        Scoreboard._dummy_count += 1
        return Scoreboard(f"dummy_{Scoreboard._dummy_count}")

    # noinspection PyMethodParameters
    @staticproperty
    @lazy
    def SYS():
        with MCFContext.INIT_STORE:
            return Scoreboard("sys")


class ScoreContainer(ABC):

    def __init__(self, identifier):
        self._identifier = identifier

    class _Container:

        def __init__(self, sc: "ScoreContainer"):
            self._sc = sc

        def __getattr__(self, item) -> "Score":
            if item.startswith('_'):
                return self.__dict__[item]
            else:
                return self._sc._get_score_(item)

        def __setattr__(self, key: str, value):
            if key.startswith('_'):
                self.__dict__[key] = value
            else:
                self._sc._set_score_(key, value)

        def __getitem__(self, item: str) -> "Score":
            if not isinstance(item, str):
                raise TypeError()
            return self._sc._get_score_(item)

        def __setitem__(self, key: str, value):
            if not isinstance(key, str):
                raise TypeError()
            return self._sc._set_score_(key, value)

    @property
    def score(self):
        """
        get score container
        """
        return ScoreContainer._Container(self)

    def _set_score_(self, k: str, v):
        with MCFContext.INIT_STORE:
            scb = Scoreboard(k)
        Score(entity=self, objective=scb).set_value(v)

    def _get_score_(self, k: str) -> "Score":
        with MCFContext.INIT_STORE:
            scb = Scoreboard(k)
        return Score(entity=self, objective=scb)


class ScoreDummy(ScoreContainer):
    """
    work like an entity, but for scoreboard only
    """
    __group_count = defaultdict(int)

    def __init__(self, name: str):
        from pymcf.entity import Name
        super(ScoreDummy, self).__init__(Name(name))

    @property
    def identifier(self):
        return self._identifier

    @staticmethod
    def new_var(group: str = "var"):
        ScoreDummy.__group_count[group] += 1
        return ScoreDummy(f'${group}_' + str(ScoreDummy.__group_count[group]))

    @staticmethod
    def const(value: int):
        return ScoreDummy(f'$const_{"n" if value < 0 else ""}{abs(value)}')


class Score(InGameData, IJsonText):

    _consts = {}

    def __init__(self,
                 value=None,
                 entity=None,
                 objective: Optional[Scoreboard] = None
                 ):
        super().__init__()
        if entity is None:
            self.entity = ScoreDummy.new_var()
            self.objective = Scoreboard.SYS if objective is None else objective
        else:
            self.entity = entity
            self.objective = Scoreboard.new_dummy() if objective is None else objective
        self.identifier = str(self.entity.identifier) + ' ' + self.objective.name

        def _init_():
            if isinstance(value, int):
                ScoreSetValueOp(self, value)
            elif isinstance(value, Score):
                ScoreCopyOp(self, value)
            elif value is None:
                pass  # don't initialize score while value is None
            else:
                ScoreSetValueOp(self, int(value))

        if not MCFContext.in_context:
            with MCFContext.INIT_VALUE:
                _init_()
        else:
            _init_()

    def _transfer_to_(self, other):
        ScoreCopyOp(other, self)

    def _structure_new_(self):
        return Score()

    def __hash__(self):
        return self.identifier.__hash__()

    def __str__(self) -> str:
        return self.identifier

    @property
    def json(self) -> JsonText:
        return JsonTextComponent({"score": {"name": str(self.entity._identifier), "objective": self.objective.name}})

    @staticmethod
    def const(value: int):
        """
        get a const score.
        :param value: const value
        :return: a const score
        """
        if value not in Score._consts:
            with MCFContext.INIT_VALUE:
                Score._consts[value] = Score(value, ScoreDummy("$const_" + str(value)), Scoreboard.SYS)
        return Score._consts[value]

    def set_value(self, value):
        """
        assignment operation for Score, just use ‘=’ instead.

        set `None` for reset.
        """
        from pymcf.data import Nbt
        if isinstance(value, int):
            ScoreSetValueOp(self, value)
        elif isinstance(value, Score):
            if value.identifier != self.identifier:
                ScoreCopyOp(self, value)
        elif value is None:
            ScoreResetValueOp(self)
        elif isinstance(value, Nbt):
            raw(f"execute store result score {self} run data get {value}")
        else:
            ScoreSetValueOp(self, int(value))

    def __lt__(self, other):
        res = Bool()
        if isinstance(other, Score):
            ScoreLTScoreOp(res, self, other)
        else:
            ScoreLTValueOp(res, self, int(other))
        return res

    def __le__(self, other):
        res = Bool()
        if isinstance(other, Score):
            ScoreLEScoreOp(res, self, other)
        else:
            ScoreLEValueOp(res, self, int(other))
        return res

    def __gt__(self, other):
        res = Bool()
        if isinstance(other, Score):
            ScoreGTScoreOp(res, self, other)
        else:
            ScoreGTValueOp(res, self, int(other))
        return res

    def __ge__(self, other):
        res = Bool()
        if isinstance(other, Score):
            ScoreGEScoreOp(res, self, other)
        else:
            ScoreGEValueOp(res, self, int(other))
        return res

    def __eq__(self, other):
        res = Bool()
        if isinstance(other, Score):
            ScoreEQScoreOp(res, self, other)
        else:
            ScoreEQValueOp(res, self, int(other))
        return res

    def __ne__(self, other):
        res = Bool()
        if isinstance(other, Score):
            ScoreNEScoreOp(res, self, other)
        else:
            ScoreNEValueOp(res, self, int(other))
        return res

    def __add__(self, other):
        res = Score(self)
        if isinstance(other, int):
            ScoreAddValueOp(res, other)
        elif isinstance(other, Score):
            ScoreAddScoreOp(res, other)
        else:
            ScoreAddValueOp(res, int(other))
        return res

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        if isinstance(other, int):
            ScoreAddValueOp(self, other)
        elif isinstance(other, Score):
            ScoreAddScoreOp(self, other)
        else:
            ScoreAddValueOp(self, int(other))
        return self

    def __sub__(self, other):
        res = Score(self)
        if isinstance(other, int):
            ScoreSubValueOp(res, other)
        elif isinstance(other, Score):
            ScoreSubScoreOp(res, other)
        else:
            ScoreSubValueOp(res, int(other))
        return res

    def __rsub__(self, other):
        res = Score(other)
        ScoreSubScoreOp(res, self)
        return res

    def __isub__(self, other):
        if isinstance(other, int):
            ScoreSubValueOp(self, other)
        elif isinstance(other, Score):
            ScoreSubScoreOp(self, other)
        else:
            ScoreSubValueOp(self, int(other))
        return self

    def __mul__(self, other):
        res = Score(self)
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreMulScoreOp(res, other)
        return res

    def __rmul__(self, other):
        return self.__mul__(other)

    def __imul__(self, other):
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreMulScoreOp(self, other)
        return self

    def __truediv__(self, other):  # TODO return Float
        res = Score(self)
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreDivScoreOp(res, other)
        return res

    def __rtruediv__(self, other):  # TODO return Float
        res = Score(other)
        ScoreDivScoreOp(res, self)
        return res

    def __itruediv__(self, other):  # TODO return Float
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreDivScoreOp(self, other)
        return self

    def __floordiv__(self, other):
        res = Score(self)
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreDivScoreOp(res, other)
        return res

    def __rfloordiv__(self, other):
        res = Score(other)
        ScoreDivScoreOp(res, self)
        return res

    def __ifloordiv__(self, other):
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreDivScoreOp(self, other)
        return self

    def __mod__(self, other):
        res = Score(self)
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreModScoreOp(res, other)
        return res

    def __imod__(self, other):
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreModScoreOp(self, other)
        return self

    def __pos__(self):
        return Score(self)

    def __neg__(self):
        res = Score(0)
        res -= self
        return res

    def __abs__(self) -> "Score":
        res = Score(self)
        neg1 = Score.const(-1)
        raw(f"execute if score {res} matches ..-1 run scoreboard players operations {res} *= {neg1}")
        return res

    def __rshift__(self, other):
        if isinstance(other, int):
            res = Score(self)
            a = Score.const(2 ** other)
            res //= a
            return res
        else:
            raise TypeError()

    def __rrshift__(self, other):
        raise TypeError()

    def __lshift__(self, other):
        if isinstance(other, int):
            res = Score(self)
            a = Score.const(2 ** other)
            res *= a
            return res
        else:
            raise TypeError()

    def __rlshift__(self, other):
        raise TypeError()

    def __bool_and__(self, other):
        if isinstance(other, Score):
            res = Bool(False)
            raw(f"execute store success score {res} unless score {self} matches 0 unless score {other} matches 0")
            return res
        else:
            return self if other else other

    def __bool_or__(self, other):
        if isinstance(other, Score):
            res = Bool()
            raw(f"execute store success score {res} unless score {self} matches 0")
            raw(f"execute if score {res} matches 0 store success score {res} unless score {other} matches 0")
            return res
        else:
            return other if other else self

    def __bool_not__(self):
        res = Bool()
        raw(f"execute store success score {res} if score {self} matches 0")  # TODO replace raw
        return res


Int = Score


class Bool(Score):
    """
    score limited in {0, 1}.
    0: False
    1: True
    """

    def _transfer_to_(self, other):
        other.set_value(self)

    def _structure_new_(self) -> "Bool":
        return Bool()

    def _compatible_to_(self, other) -> bool:
        return isinstance(other, Score)

    def __init__(
            self,
            value: Optional[bool | Any] = None,
            entity: Optional[ScoreContainer] = None,
            objective: Optional[Scoreboard] = None,
    ):
        if isinstance(value, bool):
            super().__init__(value=int(value), entity=entity, objective=objective)
        if isinstance(value, int):
            super().__init__(value=int(value != 0), entity=entity, objective=objective)
        elif value is None:
            super().__init__(value=value, entity=entity, objective=objective)
        elif isinstance(value, Bool):
            super().__init__(value=value, entity=entity, objective=objective)
        elif isinstance(value, Score):
            super().__init__(value=value, entity=entity, objective=objective)
            raw(f"execute store success score {self} unless score {self} matches 0")  # TODO replace raw
        else:
            raise TypeError(f"cannot init Bool var using {value}.")
