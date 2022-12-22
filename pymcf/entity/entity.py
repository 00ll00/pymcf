import uuid
from abc import ABC, abstractmethod
from types import FunctionType
from typing import Optional, Any, TypeVar, Mapping, final, Generic, Type

from pymcf import logger
from pymcf.data.score import ScoreContainer, Score, ScoreDummy, Scoreboard
from pymcf._frontend.context import MCFContext
from pymcf.mcversions import MCVer
from pymcf.operations.entity_ops import AddTagOp
from pymcf._project import Project
from pymcf.data.nbt import NbtCompound, EntityNbtContainer, NbtList
from pymcf.operations import raw, CallMethodOp, Operation
from pymcf.data.data import InGameEntity, InGameIterator, InGameData
from pymcf.util import Null, lazy


class Identifier(ABC):

    @abstractmethod
    def __str__(self):
        ...

    def __enter__(self):
        entity = n_Entity(identifier=self)  # TODO use Entities
        MCFContext.new_file(executor=entity)
        return entity

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
            x=Null,
            y=Null,
            z=Null,
            dx=Null,
            dy=Null,
            dz=Null,
            distance=Null,
            scores=Null,
            tags=Null,
            teams=Null,
            names=Null,
            types=Null,
            predicates=Null,
            x_rotation=Null,
            y_rotation=Null,
            nbt=Null,
            level=Null,
            gamemodes=Null,
            advancements=Null,
            limit=Null,
            sort=Null,
    ):
        return Selector(
            self._is_self,
            x=(x if x is not Null else self.x),
            y=(y if y is not Null else self.y),
            z=(z if z is not Null else self.z),
            dx=(dx if dx is not Null else self.dx),
            dy=(dy if dy is not Null else self.dy),
            dz=(dz if dz is not Null else self.dz),
            distance=(distance if distance is not Null else self.distance),
            scores=(scores if scores is not Null else self.score_),
            tags=(tags if tags is not Null else self.tag_),
            teams=(teams if teams is not Null else self.team_),
            names=(names if names is not Null else self.name_),
            types=(types if types is not Null else self.type_),
            predicates=(predicates if predicates is not Null else self.predicate_),
            x_rotation=(x_rotation if x_rotation is not Null else self.x_rotation),
            y_rotation=(y_rotation if y_rotation is not Null else self.y_rotation),
            nbt=(nbt if nbt is not Null else self.nbt),
            level=(level if level is not Null else self.level),
            gamemodes=(gamemodes if gamemodes is not Null else self.gamemode_),
            advancements=(advancements if advancements is not Null else self.advancement_),
            limit=(limit if limit is not Null else self.limit),
            sort=(sort if sort is not Null else self.sort),
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


AtS = Selector(is_self=True)


class __Not:

    def __init__(self, inner: Any):
        self.inner = inner

    def __str__(self):
        return '!' + str(self.inner)

    def __hash__(self):
        return ~hash(self.inner)


class EntityBehavior(ABC):

    def tp(self, *pos):  # TODO finish tp method
        if len(pos) == 3:
            raw(f"""tp {self} {pos[0]} {pos[1]} {pos[2]}""")
        elif isinstance(pos[0], str):
            raw(f"""tp {self} {pos[0]}""")

    def kill(self):
        raw(f"""kill {self}""")


class n_Entity(InGameEntity, ScoreContainer, EntityNbtContainer, EntityBehavior, ABC):
    """
    base class for all Entity type.
    use 'score'/'nbt' property to access all the score/nbt vars associated to this entity.
    all class inherit Entity should not define properties in `__init__` method.
    """

    __id_num = 0

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        return self

    def __init__(self, identifier: Identifier = None):
        """
        init function of an Entity class should not define properties, use `score` or `nbt` instead.
        """
        if identifier is None:
            identifier = Selector(types={self.entity_type()}, tags={self.id_tag})
        ScoreContainer.__init__(self, identifier)
        EntityNbtContainer.__init__(self, identifier)

    def __enter__(self):
        MCFContext.new_file(executor=self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        CallMethodOp(self._identifier, MCFContext.last_file().name)

    @property
    def identifier(self):
        """
        get identifier of this entity in current function context.
        """
        if MCFContext.in_context and MCFContext.current.current_file().executor is self:
            return AtS
        else:
            return self._identifier

    @classmethod
    def entity_type(cls) -> Optional[str]:
        """
        entity type fullname for selector. return None if not available.

        this method could be implemented as a classmethod or not. if this method is implemented as a normal method,
        `self` argument should set a default value to avoid argument missing exception.
        """
        return None

    @property
    @lazy
    def id_tag(self) -> str:
        """
        unique tag for instance of Entity.
        """
        n_Entity.__id_num += 1
        return f"_tag_{n_Entity.__id_num}"

    @classmethod
    def class_tag(cls) -> str:
        return f"_cls_{cls.__qualname__}"

    @classmethod
    def each_one(cls):
        return n_Entities(cls)

    @classmethod
    def selector(cls) -> Selector:
        return Selector(types={cls.entity_type()}, tags={cls.class_tag()})

    def _structure_new_(self):
        cls = type(self)
        entity = cls.__new__(cls)
        n_Entity.__init__(entity)
        return entity

    def _transfer_to_(self, other):
        AddTagOp(self, other.id_tag)


class n_Newable(n_Entity, ABC):

    @final
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.type_name = cls.entity_type()
        # noinspection PyUnresolvedReferences
        self._init_tags = [clz.class_tag() for clz in cls.mro() if
                           not clz.__name__.startswith('n_') and n_Entity in clz.mro()]
        return self

    def __init__(self, pos, nbt: Optional[NbtCompound | Mapping[str, Any]]):
        super().__init__(Selector(tags={self.id_tag}, types={self.type_name}, limit=1))
        nbt = NbtCompound.convert_from({nbt}) if nbt is not None else NbtCompound()
        if "Tags" not in nbt:
            nbt["Tags"] = NbtList()
        self._init_tags.append(self.id_tag)
        # noinspection PyUnresolvedReferences
        nbt["Tags"].extend(self._init_tags)
        raw(f"""summon {self.type_name} {pos[0]} {pos[1]} {pos[2]} {nbt._serialize() if nbt is not None else ""}""")
        MCFContext.assign_arg_entity(self)

    @classmethod
    @abstractmethod
    def entity_type(cls) -> str:
        """
        entity type full name for summon command.
        """
        ...


class n_Entities(InGameIterator, InGameEntity):  # TODO Entities should be parent class of Entity, and Entity is the special case of Entities witch limit always be 1. maybe

    def __init__(self, cls, identifier: Identifier = None):
        self._cls = cls
        self._identifier = identifier if identifier is not None else Selector(types={cls.entity_type()},
                                                                              tags={cls.class_tag()})

    def __enter__(self):
        entity = n_Entity.__new__(self._cls)
        n_Entity.__init__(entity, self._identifier)
        MCFContext.new_file(executor=entity)
        return entity

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext.exit_file()
        CallMethodOp(self.identifier, MCFContext.last_file().name)

    @property
    def identifier(self):
        if MCFContext.in_context and MCFContext.current.current_file().executor is self:
            return AtS
        else:
            return self._identifier

    def filtered(self, **kwargs) -> "n_Entities":
        """
        return Entities with modified selector
        """
        return n_Entities(self._cls, self.identifier.fork(**kwargs))

    def _iter_init_(self):
        pass

    def _iter_next_(self, brk_flag) -> InGameData:
        pass

    def _iter_end_(self):
        pass

    def _transfer_to_(self, other):
        pass

    def _structure_new_(self) -> "n_Entities":
        pass


class n_EntityHolder(n_Entity):

    def __init__(self, child_cls, identifier):
        super().__init__(identifier)
        self.child_cls = child_cls
        id_max = Score(entity=ScoreDummy("id_max"), objective=Scoreboard.SYS)
        self.score.id.set_value(id_max)
        id_max += 1

    def add_child(self, child: n_Entity):
        child.score.owner.set_value(self.score.id)

    def children_run(self, method):
        AddTagOp(self, "__eholder__")
        return n_Entities(self.child_cls).filtered()


# def entity(cls: Type):
#     """
#     entity class decorator.
#
#     apply to an inherit class of `Entity`.
#     """
#     if n_Entity not in cls.mro():
#         raise TypeError("entity decorator expect an Entity class")
#     if '__annotations__' in cls.__dict__:
#         for k, v in cls.__annotations__.items():
#             if v is Score:
#                 cls.__dict__[k] = property(
#                     lambda self: self.score[k],
#                     lambda self, value: self.score[k].set_value(value),
#                     lambda self: self.score[k].set_value(None)
#                 )
#             elif v is Nbt:
#                 cls.__dict__[k] = property(
#                     lambda self: self.nbt[k],
#                     lambda self, value: self.score[k].set_value(value),
#                     lambda self: self.score[k].set_value(None)
#                 )
