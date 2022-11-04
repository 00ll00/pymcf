import uuid
from abc import ABC, abstractmethod
from typing import Set, Optional, Dict, Any

from pymcf.datas.Score import ScoreContainer
from pymcf.context import MCFContext
from pymcf.mcversions import MCVer
from pymcf.project import Project
from pymcf.datas.nbt import NbtCompound, NbtContainer
from pymcf.operations import raw, CallMethodOp, Operation
from pymcf.datas.datas import InGameIter, InGameEntity, InGameData


class Identifier(ABC):

    @abstractmethod
    def __str__(self):
        ...


class UUID(Identifier):

    def __init__(self, name: str):
        self.uuid = uuid.uuid5(uuid.uuid1(hash(Project.namespace)), name)

    def __str__(self):
        return str(self.uuid)


class Name(Identifier):

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name


class Selector(Identifier, ABC):

    def __init__(self):
        self.x = None
        self.y = None
        self.z = None
        self.dx = None
        self.dy = None
        self.dz = None
        self.distance = None
        self.scores = set()
        self.tags = set()
        self.teams = set()
        self.names = set()
        self.types = set()
        self.predicates = set()
        self.x_rotation = None
        self.y_rotation = None
        self.nbt = None
        self.level = None
        self.gamemodes = set()
        self.advancements = set()
        self.limit = None
        self.sort = None

    def __str__(self):  # TODO finish it
        params = []
        if len(self.tags) > 0:
            params.extend(f'tag={t}' for t in self.tags)
        if self.limit is not None:
            params.append('limit={self.limit}')
        return f'@e[{", ".join(params)}]'


class __Not:

    def __init__(self, inner: Any):
        self.inner = inner

    def __str__(self):
        return '!' + str(self.inner)

    def __hash__(self):
        return ~hash(self.inner)


def tag_selector(tag: str, reverse: bool = False) -> Selector:
    self = Selector()
    if reverse:
        self.tags.add(__Not(tag))
    else:
        self.tags.add(tag)
    return self


class _Self(InGameEntity):

    def __enter__(self):
        pass  # do nothing when entering self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # do nothing when exiting self

    def __init__(self, entity: "Entity"):
        super().__init__("@s")
        self.__entity = entity

    def _unwrap_(self) -> "Entity":
        return self.__entity

    def _copy_(self):
        return self

    def _transfer_to_(self, other):
        return self

    def __getattr__(self, item) -> Any:
        # TODO
        pass

    def __setattr__(self, key, value) -> None:
        setattr(self.__entity, key, value)


class TagContainer(ABC):

    def __init__(self):
        self.__tags: Set[str] = set()

    def add_tag(self, tag: str):
        self.__tags.add(tag)

    def all_tags(self) -> Set[str]:
        return self.__tags.copy()

    def has_tag(self, tag: str) -> bool:
        return tag in self.__tags

    def del_tag(self, tag: str):
        self.__tags.remove(tag)


class Entity(ScoreContainer, NbtContainer, TagContainer, InGameEntity, ABC):

    def __init__(self, identifier: Identifier, nbt_structure: NbtCompound):
        ScoreContainer.__init__(self, identifier)
        NbtContainer.__init__(self, nbt_structure)
        TagContainer.__init__(self)
        InGameEntity.__init__(self, identifier)
        self.identifier = identifier

    def __str__(self):
        return str(self.identifier)

    def __enter__(self):
        MCFContext.new_file()
        return _Self(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        CallMethodOp(self, MCFContext.last_file().name)

    # def __getattr__(self, item):
    #     with self:
    #         if self._has_score_(item):
    #             return ScoreContainer._get_score_(self, item)


class Newable(Entity, ABC):

    def __init__(self, type_name, pos, nbt: Optional[NbtCompound]):
        self.type_name = type_name
        self._id_tag = MCFContext.new_entity_tag()
        super().__init__(tag_selector(self._id_tag))
        self._nbt["Tags"].append(self._id_tag)
        raw(f"""summon {self.type_name} {pos} {nbt.serialize() if nbt is not None else ""}""")

    def _transfer_to_(self, other: "Newable"):
        AddTagOp(self, other._id_tag)  # tag will be removed when function finished


class NormalEntity(Newable, ABC):

    def tp(self, pos):
        raw(f"""tp {self} {pos}""")

    def kill(self):
        raw(f"""kill {self}""")


class AddTagOp(Operation):

    def __init__(self, target: Entity, tag: str, offline: bool = False):
        self.target = target
        self.tag = tag
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f'tag add {self.target} {self.tag}'


class DelTagOp(Operation):

    def __init__(self, target: Entity, tag: str, offline: bool = False):
        self.target = target
        self.tag = tag
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f'tag remove {self.target} {self.tag}'


class Marker(NormalEntity):  # TODO

    def __init__(self, pos, nbt: Optional[NbtCompound]):
        super().__init__("minecraft:marker", pos, nbt)
