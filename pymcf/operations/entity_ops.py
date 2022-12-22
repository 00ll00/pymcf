from pymcf.mcversions import MCVer
from pymcf.data import InGameEntity
from pymcf.operations import Operation


class BaseEntityOp(Operation):

    def __init__(self, target: InGameEntity, offline: bool = False):
        self.target = target
        super().__init__(offline)


class AddTagOp(BaseEntityOp):

    def __init__(self, target: InGameEntity, tag: str, offline: bool = False):
        self.tag = tag
        super().__init__(target, offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f'tag {self.target} add {self.tag}'


class DelTagOp(BaseEntityOp):

    def __init__(self, target: InGameEntity, tag: str, offline: bool = False):
        self.tag = tag
        super().__init__(target, offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f'tag {self.target} remove {self.tag}'
