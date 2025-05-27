from .commands import ScoreRef, NameRef, ObjectiveRef
from ..ast_.constructor import Scope


class MCFScope(Scope):

    def __init__(self, name: str):
        super().__init__(name)
        self.consts = {}
        self.locals = []
        self.cb_name = {}
        self.sys_obj = ObjectiveRef("__sys__")

    def get_const_score(self, const: int) -> ScoreRef:
        if const not in self.consts:
            self.consts[const] = ScoreRef(NameRef(f"$const_{const}"),  self.sys_obj)
        return self.consts[const]

    def new_local_score(self) -> ScoreRef:
        index = len(self.locals)
        ref = ScoreRef(NameRef(f"$var_{index}"),  self.sys_obj)
        self.locals.append(ref)
        return ref

    def function_name(self, cb) -> str:
        if cb not in self.cb_name:
            index = len(self.cb_name)
            self.cb_name[cb] = self.name if index == 0 else f"{self.name}/sub-{index}"
        return self.cb_name[cb]
