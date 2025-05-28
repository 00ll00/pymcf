from functools import cached_property

from .commands import NameRef, Selector
from ..ast_ import Assign
from ..ast_.constructor import Scope
from ..data import ScoreBoard, Score, Entity


class MCFScope(Scope):

    def __init__(self, name: str, tags: set[str] = None, executor: Entity = None):
        super().__init__(name)
        self.executor = executor if executor is not None else Entity(Selector('s'))
        self.consts = {}
        self.locals = []
        self.cb_name = {}
        self.tags = tags or set()

    @cached_property
    def sys_scb(self) -> ScoreBoard:
        return ScoreBoard("__sys__")

    def get_const_score(self, const: int) -> Score:
        if const not in self.consts:
            self.consts[const] = Score(NameRef(f"$const_{const}"),  self.sys_scb)
            from pymcf.project import Project
            with Project.instance().scb_init_constr:
                Assign(self.consts[const], const)
        return self.consts[const]

    def new_local_score(self) -> Score:
        index = len(self.locals)
        score = Score(NameRef(f"$var_{index}"),  self.sys_scb)
        self.locals.append(score)
        return score

    def function_name(self, cb) -> str:
        if cb not in self.cb_name:
            index = len(self.cb_name)
            self.cb_name[cb] = self.name if index == 0 else f"{self.name}/sub-{index}"
        return self.cb_name[cb]

    def function_nsname(self, cb) -> str:
        name = self.function_name(cb)
        return f"{self.namespace}:{name}"