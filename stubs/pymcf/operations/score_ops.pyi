from .. import MCVer as MCVer
from .operations import Operation as Operation
from ..data import Score
from ..jsontext import JsonText


class ISVOp(Operation):
    IADD: str
    ISUB: str
    IMUL: str
    IDIV: str
    IMOD: str
    score: Score
    value: int
    op: str
    def __init__(self, score: Score, value: int, op: str, offline: bool = ...): ...


class ScoreSetValueOp(Operation):
    score: Score
    value: int
    def __init__(self, score: Score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreGetValueOp(Operation):
    score: Score
    def __init__(self, score: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreAddValueOp(Operation):
    target: Score
    value: int
    def __init__(self, score: Score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreSubValueOp(Operation):
    target: Score
    value: int
    def __init__(self, score: Score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreResetValueOp(Operation):
    target: Score
    def __init__(self, score: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreCopyOp(Operation):
    target: Score
    source: Score
    def __init__(self, target: Score, source: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreMinOp(Operation):
    left: Score
    right: Score
    def __init__(self, left: Score, right: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreMaxOp(Operation):
    left: Score
    right: Score
    def __init__(self, left: Score, right: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreAddScoreOp(Operation):
    target: Score
    source: Score
    def __init__(self, target: Score, source: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreSubScoreOp(Operation):
    target: Score
    source: Score
    def __init__(self, target: Score, source: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreMulScoreOp(Operation):
    target: Score
    source: Score
    def __init__(self, target: Score, source: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreDivScoreOp(Operation):
    target: Score
    source: Score
    def __init__(self, target: Score, source: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreModScoreOp(Operation):
    target: Score
    source: Score
    def __init__(self, target: Score, source: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreSwapScoreOp(Operation):
    target: Score
    source: Score
    def __init__(self, target: Score, source: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreEQScoreOp(Operation):
    res: Score
    left: Score
    right: Score
    def __init__(self, res: Score, left: Score, right: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreGTScoreOp(Operation):
    res: Score
    left: Score
    right: Score
    def __init__(self, res: Score, left: Score, right: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreGEScoreOp(Operation):
    res: Score
    left: Score
    right: Score
    def __init__(self, res: Score, left: Score, right: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreLTScoreOp(Operation):
    res: Score
    left: Score
    right: Score
    def __init__(self, res: Score, left: Score, right: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreLEScoreOp(Operation):
    res: Score
    left: Score
    right: Score
    def __init__(self, res: Score, left: Score, right: Score, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreEQValueOp(Operation):
    res: Score
    score: Score
    value: int
    def __init__(self, res: Score, score: Score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreGTValueOp(Operation):
    res: Score
    score: Score
    value: int
    def __init__(self, res, score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreGEValueOp(Operation):
    res: Score
    score: Score
    value: int
    def __init__(self, res, score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreLTValueOp(Operation):
    res: Score
    score: Score
    value: int
    def __init__(self, res: Score, score: Score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class ScoreLEValueOp(Operation):
    res: Score
    score: Score
    value: int
    def __init__(self, res: Score, score: Score, value: int, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class IfScoreGEValueRunOp(Operation):
    score: Score
    value: int
    action: Operation
    def __init__(self, score: Score, value: int, action: Operation, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class IfScoreLTValueRunOp(Operation):
    score: Score
    value: int
    action: Operation
    def __init__(self, score: Score, value: int, action: Operation, offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class DefScoreBoardOp(Operation):
    name: str
    type: str
    display: JsonText
    def __init__(self, name: str, scb_type: str = ..., display: JsonText | None = ..., offline: bool = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...
