from .operations import Operation
from .. import MCVer


class NbtCopyOp(Operation):

    def __init__(self, target, source):
        self.target = target
        self.source = source
        super(NbtCopyOp, self).__init__()

    def gen_code(self, mcver: MCVer) -> str:
        return f"data modify {self.target} set from {self.source}"


class NbtSetScoreOp(Operation):

    def __init__(self, target, score, dtype: str = "int", scale: float = 1):
        self.target = target
        self.score = score
        self.dtype = dtype
        self.scale = scale
        super().__init__()

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result {self.target} {self.dtype} {self.scale} run scoreboard players get {self.score}"
