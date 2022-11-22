import uuid
from abc import ABC, abstractmethod
from typing import Optional, Any, TypeVar, Mapping, final, Generic, Type

from pymcf.datas.structure import T_Entity
from pymcf.datas.score import ScoreContainer
from pymcf.context import MCFContext
from pymcf.mcversions import MCVer
from pymcf.project import Project
from pymcf.datas.nbt import NbtCompound, EntityNbtContainer, NbtList
from pymcf.operations import raw, CallMethodOp, Operation
from pymcf.datas.datas import InGameEntity, InGameIter, InGameData
from pymcf.util import _ParamEmpty


class Identifier(ABC):

    @abstractmethod
    def __str__(self):
        ...

    def __enter__(self):
        MCFContext.new_file()
        return _Self(_Entity(self))

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        CallMethodOp(self, MCFContext.last_file().name)


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
            x=None,
            y=None,
            z=None,
            dx=None,
            dy=None,
            dz=None,
            distance=None,
            scores=None,
            tags=None,
            teams=None,
            names=None,
            types=None,
            predicates=None,
            x_rotation=None,
            y_rotation=None,
            nbt=None,
            level=None,
            gamemodes=None,
            advancements=None,
            limit=None,
            sort=None,
    ):
        self._is_self = is_self
        self.x = x
        self.y = y
        self.z = z
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.distance = distance
        self.score_ = scores if scores is not None else set()
        self.tag_ = tags if tags is not None else set()
        self.team_ = teams if teams is not None else set()
        self.name_ = names if names is not None else set()
        self.type_ = types if types is not None else set()
        self.predicate_ = predicates if predicates is not None else set()
        self.x_rotation = x_rotation
        self.y_rotation = y_rotation
        self.nbt = nbt
        self.level = level
        self.gamemode_ = gamemodes if gamemodes is not None else set()
        self.advancement_ = advancements if advancements is not None else set()
        self.limit = limit
        self.sort = sort

    def fork(
            self,
            x=_ParamEmpty,
            y=_ParamEmpty,
            z=_ParamEmpty,
            dx=_ParamEmpty,
            dy=_ParamEmpty,
            dz=_ParamEmpty,
            distance=_ParamEmpty,
            scores=_ParamEmpty,
            tags=_ParamEmpty,
            teams=_ParamEmpty,
            names=_ParamEmpty,
            types=_ParamEmpty,
            predicates=_ParamEmpty,
            x_rotation=_ParamEmpty,
            y_rotation=_ParamEmpty,
            nbt=_ParamEmpty,
            level=_ParamEmpty,
            gamemodes=_ParamEmpty,
            advancements=_ParamEmpty,
            limit=_ParamEmpty,
            sort=_ParamEmpty,
    ):
        return Selector(
            self._is_self,
            x=(x if x is not _ParamEmpty else self.x),
            y=(y if y is not _ParamEmpty else self.y),
            z=(z if z is not _ParamEmpty else self.z),
            dx=(dx if dx is not _ParamEmpty else self.dx),
            dy=(dy if dy is not _ParamEmpty else self.dy),
            dz=(dz if dz is not _ParamEmpty else self.dz),
            distance=(distance if distance is not _ParamEmpty else self.distance),
            scores=(scores if scores is not _ParamEmpty else self.score_),
            tags=(tags if tags is not _ParamEmpty else self.tag_),
            teams=(teams if teams is not _ParamEmpty else self.team_),
            names=(names if names is not _ParamEmpty else self.name_),
            types=(types if types is not _ParamEmpty else self.type_),
            predicates=(predicates if predicates is not _ParamEmpty else self.predicate_),
            x_rotation=(x_rotation if x_rotation is not _ParamEmpty else self.x_rotation),
            y_rotation=(y_rotation if y_rotation is not _ParamEmpty else self.y_rotation),
            nbt=(nbt if nbt is not _ParamEmpty else self.nbt),
            level=(level if level is not _ParamEmpty else self.level),
            gamemodes=(gamemodes if gamemodes is not _ParamEmpty else self.gamemode_),
            advancements=(advancements if advancements is not _ParamEmpty else self.advancement_),
            limit=(limit if limit is not _ParamEmpty else self.limit),
            sort=(sort if sort is not _ParamEmpty else self.sort),
        )

    def __str__(self):  # TODO finish it
        params = []
        for k, v in self.__dict__.items():
            if k.startswith('_'):
                continue
            if k.endswith('_'):
                if len(v) > 0:
                    params.extend(f'{k[:-1]}={vv}' for vv in v)
            else:
                if v is not None:
                    params.append(f'{k}={v}')

        return ('@s' if self._is_self else '@e') + (f'[{", ".join(params)}]' if params else "")


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


__Entity = TypeVar("__Entity", bound=T_Entity)


class _Entity(InGameEntity, ScoreContainer, EntityNbtContainer[__Entity], ABC):

    def __init__(self, identifier: Identifier):
        """
        init function of an Entity class should not define properties, use `score` or `nbt` instead
        """
        InGameEntity.__init__(self, identifier)
        ScoreContainer.__init__(self, identifier)
        EntityNbtContainer.__init__(self, identifier)

    def __enter__(self):
        MCFContext.new_file()
        return _Self(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        CallMethodOp(self._identifier, MCFContext.last_file().name)

    @classmethod
    def class_tag(cls) -> str:
        return f"{Project.namespace}.cls_{cls.__qualname__}"

    def _new_from_(self) -> "_Entity":
        return _Entity(Selector(tags={MCFContext.new_entity_tag()}))

    def _transfer_to_(self, other):
        AddTagOp(self, other._id_tag)  # TODO


_T_E = TypeVar("_T_E", bound=_Entity)


class _Newable(_Entity[__Entity], ABC):

    @classmethod
    @abstractmethod
    def entity_type(cls) -> str:
        ...

    @final
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.type_name = cls.entity_type()
        # noinspection PyUnresolvedReferences
        self._init_tags = [clz.class_tag() for clz in cls.mro() if
                           not clz.__name__.startswith('_') and _Entity in clz.mro()]
        return self

    def __init__(self, pos, nbt: Optional[NbtCompound | Mapping[str, Any]]):
        self._id_tag = MCFContext.new_entity_tag()
        super().__init__(Selector(tags={self._id_tag}, types={self.type_name}, limit=1))
        nbt = NbtCompound.convert_from({nbt}) if nbt is not None else NbtCompound()
        if "Tags" not in nbt:
            nbt["Tags"] = NbtList()
        self._init_tags.append(self._id_tag)
        # noinspection PyUnresolvedReferences
        nbt["Tags"].extend(self._init_tags)
        raw(f"""summon {self.type_name} {pos[0]} {pos[1]} {pos[2]} {nbt._serialize() if nbt is not None else ""}""")

    @classmethod
    def instances(cls: Type[_T_E]) -> "_Entities[_T_E]":
        return _Entities(cls)

    @classmethod
    def selector(cls) -> Selector:
        return Selector(types={cls.entity_type()}, tags={cls.class_tag()})

    def _transfer_to_(self, other: "_Newable"):
        AddTagOp(self, other._id_tag)  # TODO tag will be removed when function finished


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


class _Entities(InGameIter[_T_E], Generic[_T_E]):

    def __init__(self, cls, identifier: Identifier = None):
        self._cls = cls
        self._identifier = identifier if identifier is not None else Selector(types={cls.entity_type()}, tags={cls.class_tag()})

    def __enter__(self) -> _T_E:
        MCFContext.new_file()
        entity = object.__new__(self._cls)
        _Entity.__init__(entity, self._identifier)
        for k, v in self._cls.__dict__.items():
            if isinstance(v, staticmethod):
                entity.__dict__[k] = v
        # noinspection PyTypeChecker
        return _Self(entity)

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        CallMethodOp(self._identifier, MCFContext.last_file().name)

    def filtered(self, **kwargs) -> "_Entities[_T_E]":
        """
        return Entities with modified selector
        """
        return _Entities(self._cls, self._identifier.fork(**kwargs))

    def _iter_init(self):
        pass

    def _iter_next(self, brk_flag) -> InGameData:
        pass

    def _transfer_to_(self, other):
        pass

    def _new_from_(self) -> "_Entities[_T_E]":
        pass


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


class __Marker(T_Entity):
    data: NbtCompound


class Marker(_NormalEntity[__Marker]):  # TODO

    @classmethod
    def entity_type(cls) -> str:
        return "minecraft:marker"

    def __init__(self, pos, nbt: Optional[NbtCompound]):
        super().__init__(pos, nbt)
