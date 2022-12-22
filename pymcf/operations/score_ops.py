from .operations import Operation
from .. import MCVer
from ..jsontext import JsonText


class BaseScoreOp(Operation):
    pass


class ISVOp(BaseScoreOp):
    """
    inplace score value operation.
    """

    IADD = 'IADD'
    ISUB = 'ISUB'
    IMUL = 'IMUL'
    IDIV = 'IDIV'
    IMOD = 'IMOD'

    def __init__(self, score, value, op, offline=False):
        self.score = score
        self.value = value
        self.op = op
        if op in {ISVOp.IMUL, ISVOp.IDIV, ISVOp.IMOD}:
            from pymcf.data.score import Score
            self.value = Score.const(value)
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        match self.op:
            case ISVOp.IADD:
                return f"scoreboard players add {self.score} {self.value}"
            case ISVOp.ISUB:
                return f"scoreboard players remove {self.score} {self.value}"
            case ISVOp.IMUL:
                return f"scoreboard players operation {self.score} *= {self.value}"
            case ISVOp.IMUL:
                return f"scoreboard players operation {self.score} /= {self.value}"
            case ISVOp.IMOD:
                return f"scoreboard players operation {self.score} %= {self.value}"


class ScoreSetValueOp(BaseScoreOp):

    def __init__(self, score, value: int, offline: bool = False):
        self.score = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players set {self.score} {self.value}"


class ScoreGetValueOp(Operation):

    def __init__(self, score, offline: bool = False):
        self.score = score

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players get {self.score}"


class ScoreAddValueOp(Operation):

    def __init__(self, score, value: int, offline: bool = False):
        self.target = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players add {self.target} {self.value}"


class ScoreSubValueOp(Operation):

    def __init__(self, score, value: int, offline: bool = False):
        self.target = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players remove {self.target} {self.value}"


class ScoreResetValueOp(Operation):

    def __init__(self, score, offline: bool = False):
        self.target = score

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players reset {self.target}"


class ScoreCopyOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target = target
        self.source = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} = {self.source}"


class ScoreMinOp(Operation):

    def __init__(self, left, right, offline: bool = False):
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.left} < {self.right}"


class ScoreMaxOp(Operation):

    def __init__(self, left, right, offline: bool = False):
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.left} > {self.right}"


class ScoreAddScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target = target
        self.source = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} += {self.source}"


class ScoreSubScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target = target
        self.source = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} -= {self.source}"


class ScoreMulScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target = target
        self.source = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} *= {self.source}"


class ScoreDivScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target = target
        self.source = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} /= {self.source}"


class ScoreModScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target = target
        self.source = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} %= {self.source}"


class ScoreSwapScoreOp(Operation):

    def __init__(self, target, source, offline: bool = False):
        self.target = target
        self.source = source

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard players operation {self.target} >< {self.source}"


class ScoreEQScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res = res
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.left} = {self.right}"


class ScoreNEScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res = res
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} unless score {self.left} = {self.right}"


class ScoreGTScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res = res
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.left} > {self.right}"


class ScoreGEScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res = res
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.left} >= {self.right}"


class ScoreLTScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res = res
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.left} < {self.right}"


class ScoreLEScoreOp(Operation):

    def __init__(self, res, left, right, offline: bool = False):
        self.res = res
        self.left = left
        self.right = right

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.left} <= {self.right}"


class ScoreEQValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res = res
        self.score = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.score} matches {self.value}"


class ScoreNEValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res = res
        self.score = score
        self.value: int = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} unless score {self.score} matches {self.value}"


class ScoreGTValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res = res
        self.score = score
        self.value = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.score} matches {self.value + 1}.."


class ScoreGEValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res = res
        self.score = score
        self.value = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.score} matches {self.value}.."


class ScoreLTValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res = res
        self.score = score
        self.value = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.score} matches ..{self.value - 1}"


class ScoreLEValueOp(Operation):

    def __init__(self, res, score, value, offline: bool = False):
        self.res = res
        self.score = score
        self.value = value

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store success score {self.res} if score {self.score} matches ..{self.value}"


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

    def __init__(self, name: str, scb_type: str = "dummy", display: JsonText = None, offline: bool = False):
        self.name = name
        self.type = scb_type
        self.display = display if display is not None else ""

        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f"scoreboard objectives add {self.name} {self.type} {self.display}"
