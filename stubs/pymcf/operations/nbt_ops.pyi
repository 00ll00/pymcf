from typing import Any

from .. import MCVer as MCVer
from .operations import Operation as Operation
from ..data import Nbt, Score, NbtData


class NbtCopyOp(Operation):
    target: Nbt
    source: Nbt
    def __init__(self, target: Nbt, source: Nbt) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...

class NbtSetScoreOp(Operation):
    target: Nbt
    score: Score
    dtype: str
    scale: float
    def __init__(self, target: Nbt, score: Score, dtype: str = ..., scale: float = ...) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...


class NbtSetValueOp(Operation):
    target: Nbt
    value: NbtData
    def __init__(self, target: Nbt, value: NbtData) -> None: ...
    def gen_code(self, mcver: MCVer) -> str: ...