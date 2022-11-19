import uuid
from abc import ABC, abstractmethod
from typing import Set, Optional, Any, TypeVar, Mapping

from pymcf.datas.structure import _T_Entity
from pymcf.datas.score import ScoreContainer
from pymcf.context import MCFContext
from pymcf.mcversions import MCVer
from pymcf.project import Project
from pymcf.datas.nbt import NbtCompound, EntityNbtContainer, NbtData, NbtList
from pymcf.operations import raw, CallMethodOp, Operation
from pymcf.datas.datas import InGameEntity
from pymcf.util import staticproperty


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


class Selector(Identifier):

    def __init__(
            self,
            is_self: bool = False,
            x = None,
            y = None,
            z = None,
            dx = None,
            dy = None,
            dz = None,
            distance = None,
            scores = None,
            tags = None,
            teams = None,
            names = None,
            types = None,
            predicates = None,
            x_rotation = None,
            y_rotation = None,
            nbt = None,
            level = None,
            gamemodes = None,
            advancements = None,
            limit = None,
            sort = None,
    ):
        self.is_self = is_self
        self.x = x
        self.y = y
        self.z = z
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.distance = distance
        self.scores = scores if scores is not None else set()
        self.tags = tags if tags is not None else set()
        self.teams = teams if teams is not None else set()
        self.names = names if names is not None else set()
        self.types = types if types is not None else set()
        self.predicates = predicates if predicates is not None else set()
        self.x_rotation = x_rotation
        self.y_rotation = y_rotation
        self.nbt = nbt
        self.level = level
        self.gamemodes = gamemodes if gamemodes is not None else set()
        self.advancements = advancements if advancements is not None else set()
        self.limit = limit
        self.sort = sort

    def __str__(self):  # TODO finish it
        params = []
        if len(self.types) > 0:
            params.extend(f'type={t}' for t in self.types)
        if len(self.tags) > 0:
            params.extend(f'tag={t}' for t in self.tags)
        if self.limit is not None:
            params.append(f'limit={self.limit}')

        return ('@s' if self.is_self else '@e') + (f'[{", ".join(params)}]' if params else "")


class __Not:

    def __init__(self, inner: Any):
        self.inner = inner

    def __str__(self):
        return '!' + str(self.inner)

    def __hash__(self):
        return ~hash(self.inner)


class _Self(InGameEntity):

    def __enter__(self):
        pass  # do nothing when entering self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # do nothing when exiting self

    def __init__(self, entity: "_Entity"):
        self._entity = entity
        self._origin_identifier = entity._identifier
        super().__init__(Selector(is_self=True))
        self._entity._identifier = self._identifier

    def _unwrap_(self) -> "_Entity":
        self._entity._identifier = self._origin_identifier
        return self._entity

    def _new_from_(self):
        return self

    def _transfer_to_(self, other):
        # noinspection PyTypeChecker
        AddTagOp(self, other._id_tag)

    def __getattr__(self, item) -> Any:
        if item.startswith("_"):
            return self.__dict__[item]
        else:
            return getattr(self._entity, item)

    def __setattr__(self, key: str, value) -> None:
        if key.startswith("_"):
            self.__dict__[key] = value
        else:
            setattr(self._entity, key, value)


__Entity = TypeVar("__Entity", bound=_T_Entity)


class _Entity(InGameEntity, ScoreContainer, EntityNbtContainer[__Entity], ABC):

    def __init__(self, identifier: Identifier):
        InGameEntity.__init__(self, identifier)
        ScoreContainer.__init__(self, identifier)
        EntityNbtContainer.__init__(self, identifier)

    def __enter__(self):
        MCFContext.new_file()
        return _Self(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        CallMethodOp(self, MCFContext.last_file().name)

    @classmethod
    def class_tag(cls) -> str:
        return f"{Project.namespace}.cls_{cls.__qualname__}"

    @classmethod
    def instances(cls) -> Selector:
        return Selector()


class _Newable(_Entity[__Entity], ABC):

    @classmethod
    @abstractmethod
    def _entity_type(cls) -> str:
        ...

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.type_name = cls._entity_type()
        self._init_tags = [clz.class_tag() for clz in cls.mro() if not clz.__name__.startswith('_') and _Entity in clz.mro()]
        return self

    def __init__(self, pos, nbt: Optional[NbtCompound | Mapping[str, Any]]):
        self._id_tag = MCFContext.new_entity_tag()
        super().__init__(Selector(tags={self._id_tag}, types={self.type_name}, limit=1))
        nbt = NbtCompound.convert_from({nbt}) if nbt is not None else NbtCompound()
        if "Tags" not in nbt:
            nbt["Tags"] = NbtList()
        self._init_tags.append(self._id_tag)
        nbt["Tags"].extend(self._init_tags)
        raw(f"""summon {self.type_name} {pos[0]} {pos[1]} {pos[2]} {nbt._serialize() if nbt is not None else ""}""")

    @classmethod
    def instances(cls) -> Selector:
        return Selector(types={cls._entity_type()}, tags={cls.class_tag()})

    def _transfer_to_(self, other: "_Newable"):
        AddTagOp(self, other._id_tag)  # tag will be removed when function finished


class _NormalEntity(_Newable[__Entity], ABC):

    def tp(self, *pos):
        if len(pos) == 3:
            raw(f"""tp {self} {pos[0]} {pos[1]} {pos[2]}""")
        elif isinstance(pos[0], str):
            raw(f"""tp {self} {pos[0]}""")

    def kill(self):
        raw(f"""kill {self}""")

    def _new_from_(self):
        return self


class AddTagOp(Operation):

    def __init__(self, target: InGameEntity, tag: str, offline: bool = False):
        self.target = target
        self.tag = tag
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f'tag add {self.target} {self.tag}'


class DelTagOp(Operation):

    def __init__(self, target: InGameEntity, tag: str, offline: bool = False):
        self.target = target
        self.tag = tag
        super().__init__(offline)

    def gen_code(self, mcver: MCVer) -> str:
        return f'tag remove {self.target} {self.tag}'


class __Marker(_T_Entity):
    data: NbtCompound


class Marker(_NormalEntity[__Marker]):  # TODO

    @classmethod
    def _entity_type(cls) -> str:
        return "minecraft:marker"

    def __init__(self, pos, nbt: Optional[NbtCompound]):
        super().__init__(pos, nbt)
