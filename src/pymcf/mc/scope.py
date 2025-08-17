from functools import cached_property
from hashlib import md5

from pymcf.mc.commands import EntityRef, NbtPath, Storage

from .commands import NameRef, AtS
from ..ast_ import Assign
from ..ast_.constructor import Scope
from ..data import ScoreBoard, Score, Entity, Nbt


class MCFScope(Scope):

    def __init__(self, name: str, tags: set[str] = None, executor: Entity = None, set_throws=None, macro: bool = False):
        super().__init__(name, set_throws)

        self.local_namespace = md5(self.name.encode()).hexdigest()[:8]

        self.executor = executor
        self.consts = {}
        self.locals = []
        self.cb_name = {}
        self.tags = tags or set()
        self.macro = macro

    @cached_property
    def sys_scb(self) -> ScoreBoard:
        return ScoreBoard("__sys__")

    @cached_property
    def sys_storage(self) -> Storage:
        from ..project import Project
        return Storage(f"{Project.instance().name.lower()}:__sys__")  # TODO self.namespace 为什么是 None

    def get_const_score(self, const: int) -> Score:
        if const not in self.consts:
            self.consts[const] = Score(NameRef(f"$const_{const}"),  self.sys_scb)
            from pymcf.project import Project
            with Project.instance().scb_init_constr:  # TODO 消除冗余的常量赋值
                Assign(self.consts[const], const)
        return self.consts[const]

    def next_local_var_name(self) -> str:
        index = len(self.locals)
        return f"{self.local_namespace}_{index}"  # TODO 变量作用域区分

    def new_local_score(self) -> Score:
        score = Score(NameRef("$var_" + self.next_local_var_name()),  self.sys_scb)
        self.locals.append(score)
        return score

    def new_local_nbt(self) -> Nbt:
        nbt = Nbt(self.sys_storage, NbtPath('vars') + NbtPath(self.next_local_var_name()))
        self.locals.append(nbt)
        return nbt

    def new_local_entity_tag(self) -> str:
        tag = f"{self.namespace}.var_{self.next_local_var_name()}"
        self.locals.append(tag)  # TODO 应当将实体对象作为 local 变量进行添加，而不是 tag
        return tag

    @property
    def nsname(self):
        return f"{self.namespace}:{self.name}"

    def sub_name(self, cb) -> str:
        if cb not in self.cb_name:
            index = len(self.cb_name)
            self.cb_name[cb] = self.name if index == 0 else f"{self.name}/sub-{index}"
        return self.cb_name[cb]

    def sub_nsname(self, cb) -> str:
        name = self.sub_name(cb)
        return f"{self.namespace}:{name}"

    def resolve_entity(self, entity: EntityRef) -> str | None:
        if self.executor is not None and self.executor.__metadata__ == entity:
            return '@s'
        return None