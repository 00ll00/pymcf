from pymcf.mcversions import MCVer
from pymcf.data import InGameEntity
from pymcf.operations import Operation


class BaseEntityOp(Operation):
    target: InGameEntity
    def __init__(self, target: InGameEntity, offline: bool = False):


class AddTagOp(BaseEntityOp):
    def __init__(self, target: InGameEntity, tag: str, offline: bool = ...): ...
    def gen_code(self, mcver: MCVer) -> str: ...

class DelTagOp(BaseEntityOp):
    def __init__(self, target: InGameEntity, tag: str, offline: bool = ...): ...
    def gen_code(self, mcver: MCVer) -> str: ...