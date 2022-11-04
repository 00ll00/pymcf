from abc import ABC
from collections import defaultdict
from typing import Optional, Any, Dict

from pymcf.context import MCFContext
from pymcf.datas.datas import InGameData
from pymcf.mcversions import MCVer
from pymcf.operations import Operation
from pymcf.util import staticproperty, lazy


class ScoreSetValueOp(Operation):

    def __init__(self, score, value: int, offline: bool = False):
        self.score: Score = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players set {self.score} {self.value}"


class ScoreGetValueOp(Operation):

    def __init__(self, score, offline: bool = False):
        self.score: Score = score

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players get {self.score}"


class ScoreAddValueOp(Operation):

    def __init__(self, score, value: int, offline: bool = False):
        self.target: Score = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players add {self.target} {self.value}"


class ScoreSubValueOp(Operation):

    def __init__(self, score, value: int, offline: bool = False):
        self.target: Score = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players remove {self.target} {self.value}"


class ScoreResetValueOp(Operation):

    def __init__(self, score, offline: bool = False):
        self.target: Score = score

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players reset {self.target}"


class ScoreCopyOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target: Score = target
        self.source: Score = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} = {self.source}"


class ScoreMinOp(Operation):

    def __init__(self, left, right, offline: bool = False):
        self.left: Score = left
        self.right: Score = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.left} < {self.right}"


class ScoreMaxOp(Operation):

    def __init__(self, left, right, offline: bool = False):
        self.left: Score = left
        self.right: Score = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.left} > {self.right}"


class ScoreAddScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target: Score = target
        self.source: Score = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} += {self.source}"


class ScoreSubScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target: Score = target
        self.source: Score = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} -= {self.source}"


class ScoreMulScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target: Score = target
        self.source: Score = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} *= {self.source}"


class ScoreDivScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target: Score = target
        self.source: Score = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} /= {self.source}"


class ScoreModScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target: Score = target
        self.source: Score = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} %= {self.source}"


class ScoreSwapScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target: Score = target
        self.source: Score = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} >< {self.source}"


class ScoreEQScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res: Score = res
        self.left: Score = left
        self.right: Score = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.left} = {self.right}"


class ScoreGTScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res: Score = res
        self.left: Score = left
        self.right: Score = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.left} > {self.right}"


class ScoreGEScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res: Score = res
        self.left: Score = left
        self.right: Score = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.left} >= {self.right}"


class ScoreLTScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res: Score = res
        self.left: Score = left
        self.right: Score = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.left} < {self.right}"


class ScoreLEScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res: Score = res
        self.left: Score = left
        self.right: Score = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.left} <= {self.right}"


class ScoreEQValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res: Score = res
        self.score: Score = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.score} matches {self.value}"


class ScoreGTValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res: Score = res
        self.score: Score = score
        self.value: Score = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.score} matches {self.value + 1}.."


class ScoreGEValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res: Score = res
        self.score: Score = score
        self.value: Score = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.score} matches {self.value}.."


class ScoreLTValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res: Score = res
        self.score: Score = score
        self.value: Score = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.score} matches ..{self.value - 1}"


class ScoreLEValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res: Score = res
        self.score: Score = score
        self.value: Score = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result score {self.res} if score {self.score} matches ..{self.value}"


class IfScoreGEValueRunOp(Operation):

    def __init__(self, score, value: int, action: Operation, offline: bool = False):
        assert action.offline

        self.score = score
        self.value = value
        self.action = action

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute if score {self.score} matches {self.value}.. run {self.action.gen_code(mcver)}"


class IfScoreLTValueRunOp(Operation):

    def __init__(self, score, value: int, action: Operation, offline: bool = False):
        assert action.offline

        self.score = score
        self.value = value
        self.action = action

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute unless score {self.score} matches {self.value}.. run {self.action.gen_code(mcver)}"


class DefScoreBoardOp(Operation):

    def __init__(self, name: str, scb_type: str = "dummy", display=None, offline: bool = False):
        self.name = name
        self.type = scb_type
        self.display = display

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard objectives add {self.name} {self.type}"


class Scoreboard:
    _dummy_count = 0

    def __init__(self, name: str, scb_type: str = "dummy"):
        self.name = name
        self.type = scb_type

        def _init_():
            DefScoreBoardOp(self.name, self.type)

        if not MCFContext.in_context:
            with MCFContext.INIT_STORE:
                _init_()
        else:
            _init_()

    def __str__(self):
        return self.name

    @staticmethod
    def new_dummy():
        Scoreboard._dummy_count += 1
        return Scoreboard(f"dummy_{Scoreboard._dummy_count}")

    # noinspection PyMethodParameters
    @staticproperty
    @lazy
    def SYS():
        return Scoreboard("sys")


class ScoreContainer(ABC):

    def __init__(self, identifier):
        self.__scores: Dict[str, Score] = {}
        self.identifier = identifier

    def _set_score_(self, k: str, v):
        if k not in self.__scores:
            self.__scores[k] = Score(entity=self, objective=Scoreboard(k))
        self.__scores[k].set(v)

    def _get_score_(self, k: str) -> "Score":
        return self.__scores[k]

    def _has_score_(self, k: str) -> bool:
        return k in self.__scores


class ScoreDummy(ScoreContainer):
    """
    work like an entity, but for scoreboard only
    """
    __group_count = defaultdict(int)

    def __init__(self, name: str):
        from pymcf.datas.entity.Entity import Name
        super(ScoreDummy, self).__init__(Name(name))

    @staticmethod
    def new_var(group: str = "var"):
        ScoreDummy.__group_count[group] += 1
        return ScoreDummy(f'${group}_' + str(ScoreDummy.__group_count[group]))

    @staticmethod
    def const(value: int):
        return ScoreDummy(f'$const_{"n" if value < 0 else ""}{abs(value)}')


class Score(InGameData):
    _consts = {}

    def __init__(self,
                 value: Optional[int | Any] = None,
                 entity: Optional[ScoreContainer] = None,
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
            with MCFContext.INIT_SCORE:
                _init_()
        else:
            _init_()

    def _transfer_to_(self, other):
        ScoreCopyOp(other, self)

    def _copy_(self):
        return Score(self)

    def __hash__(self):
        return self.identifier.__hash__()

    def __str__(self) -> str:
        return self.identifier

    @property
    def json(self):
        return f"""{{"score": {{"name": "{self.entity.identifier}", "objective": "{self.objective.name}" }} }}"""  # TODO json text

    @staticmethod
    def const(value: int):
        """
        get a const score.
        :param value: const value
        :return: a const score
        """
        if value not in Score._consts:
            with MCFContext.INIT_SCORE:
                Score._consts[value] = Score(value, ScoreDummy("$const_" + str(value)), Scoreboard.SYS)
        return Score._consts[value]

    def set(self, value):
        """
        assignment operation for Score, just use ‘=’ instead.

        set `None` for reset.
        """
        if isinstance(value, int):
            ScoreSetValueOp(self, value)
        elif isinstance(value, Score):
            if value.identifier != self.identifier:
                ScoreCopyOp(self, value)
        elif value is None:
            ScoreResetValueOp(self)
        else:
            ScoreSetValueOp(self, int(value))

    def __lt__(self, other):
        res = Score(0)
        if isinstance(other, Score):
            ScoreLTScoreOp(res, self, other)
        else:
            ScoreLTValueOp(res, self, int(other))
        return res

    def __le__(self, other):
        res = Score(0)
        if isinstance(other, Score):
            ScoreLEScoreOp(res, self, other)
        else:
            ScoreLEValueOp(res, self, int(other))
        return res

    def __gt__(self, other):
        res = Score(0)
        if isinstance(other, Score):
            ScoreGTScoreOp(res, self, other)
        else:
            ScoreGTValueOp(res, self, int(other))
        return res

    def __ge__(self, other):
        res = Score(0)
        if isinstance(other, Score):
            ScoreGEScoreOp(res, self, other)
        else:
            ScoreGEValueOp(res, self, int(other))
        return res

    def __eq__(self, other):
        res = Score(0)
        if isinstance(other, Score):
            ScoreEQScoreOp(res, self, other)
        else:
            ScoreEQValueOp(res, self, int(other))
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

    def __imul__(self, other):
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreMulScoreOp(self, other)
        return self

    def __truediv__(self, other):
        res = Score(self)
        if not isinstance(other, Score):
            other = Score.const(int(other))
        ScoreDivScoreOp(res, other)
        return res

    def __itruediv__(self, other):
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
