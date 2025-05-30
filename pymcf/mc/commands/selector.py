from abc import ABC
from typing import Literal, overload, Any, Self

from .core import Resolvable, EntityRef
from .scoreboard import ObjectiveRef


class NumRange(Resolvable):

    def __init__(self, min=None, max=None):
        assert min is not None or max is not None
        self.min = min
        self.max = max

    def resolve(self, scope):
        range = ''
        if self.min is not None:
            range = '%d' % self.min
        if self.max is not None and self.max != self.min:
            range += '..%d' % self.max
        elif self.max is None:
            range += '..'
        return range


class SelectorArgs(Resolvable, ABC):
    pass

class SelRange(SelectorArgs):
    def __init__(self, objective, min=None, max=None):
        assert isinstance(objective, ObjectiveRef)
        self.objective = objective
        self.range = NumRange(min, max)

    def resolve(self, scope):
        return {'scores': {self.objective.resolve(scope):
                               self.range.resolve(scope)}}

class SelEquals(SelRange):
    def __init__(self, objective, value):
        super().__init__(objective, value, value)

class SelNbt(SelectorArgs):

    def __init__(self, path, value):
        self.nbt_spec = {}
        if not path:
            self.nbt_spec = value
        else:
            self.build_selector(path, self.nbt_spec, value)

    def build_selector(self, path, parent, value):
        for i in range(len(path) - 1):
            node = path[i]
            if node.isdigit():
                pos = int(node)
                while len(parent) < pos + 1:
                    parent.append({})
                parent = parent[pos]
                continue
            if node not in parent:
                parent[node] = {}
            if len(path) > i + 1:
                if path[i+1].isdigit():
                    if not parent[node]:
                        parent[node] = []
                    else:
                        assert type(parent[node]) == list
            parent = parent[node]
        if path[-1].isdigit():
            pos = int(path[-1])
            while len(parent) < pos + 1:
                parent.append({})
            path[-1] = pos
        parent[path[-1]] = value

    def stringify_nbt(self, node, scope):
        # TODO quoted keys
        if type(node) == dict:
            return '{%s}' % ','.join('%s:%s' % (k, self.stringify_nbt(v, scope))
                                     for k,v in node.items())
        if type(node) == list:
            return '[%s]' % ','.join(map(lambda n:self.stringify_nbt(n, scope), node))
        if isinstance(node, Resolvable):
            return node.resolve(scope)
        assert False, type(node)

    def resolve(self, scope):
        return {'nbt': self.stringify_nbt(self.nbt_spec, scope)}

class SelTags(SelectorArgs):

    def __init__(self, tags: set[str]):
        self.tags = tags

    def resolve(self, scope):
        return ','.join(f"tag={tag}" for tag in self.tags)

class SelectorProto:
    advancements: Any = None
    distance: NumRange = None
    dx: int = None
    dy: int = None
    dz: int = None
    gamemode: Literal["adventure", "creative", "spectator", "survival", "!adventure", "!creative", "!spectator", "!survival"] = None
    level: int = None
    limit: int = None
    name: str = None
    nbt: list[SelNbt] | SelNbt = None
    predicate: Any = None
    scores: list[SelRange] | SelRange = None
    sort: Literal["arbitrary", "furthest", "nearest", "random"] = None
    tag: SelTags = None
    team: str = None
    type: str = None
    x: int = None
    x_rotation: NumRange = None
    y: int = None
    y_rotation: NumRange = None
    z: int = None

class Selector(EntityRef, SelectorProto):

    _NotAvailable = object()

    _kind: Literal['a', 'e', 'n', 'p', 'r', 's'] = None
    _solid: dict = {}
    _soft: dict = {}

    @overload
    def __init__(
            self,
            advancements=None,
            distance: NumRange = None,
            dx: int = None,
            dy: int = None,
            dz: int = None,
            gamemode: Literal["adventure", "creative", "spectator", "survival", "!adventure", "!creative", "!spectator", "!survival",] = None,
            level: int = None,
            limit: int = None,
            name: str = None,
            nbt: SelNbt = None,
            predicate=None,
            scores: list[SelRange] | SelRange = None,
            sort: Literal["arbitrary", "furthest", "nearest", "random"] = None,
            tag: SelTags | set[str] | str = None,
            team: str = None,
            type: str = None,
            x: int = None,
            x_rotation: NumRange = None,
            y: int = None,
            y_rotation: NumRange = None,
            z: int = None,
    ): ...

    def __init__(self, **kwargs):
        assert self._kind is not None
        self.__dict__.update({k: Selector._NotAvailable for k in self._solid})
        self._update(kwargs)

    def _update(self, kwargs):
        for k, v in kwargs.copy().items():
            if v is self._NotAvailable:
                kwargs.pop(k)

        for k in kwargs:
            if self.__dict__.get(k) is Selector._NotAvailable:
                raise KeyError()

        for k in kwargs:
            if k == "tag" and not isinstance(kwargs[k], SelTags):
                tags = SelTags(kwargs[k] if isinstance(kwargs[k], set) else {kwargs[k]})
                if isinstance(self.tag, SelTags):
                    tags |= self.tag.tags
                kwargs[k] = tags
            elif k == "nbt":
                ...  # TODO
            elif k == "predicate":
                ...  # TODO

        self.__dict__.update(kwargs)

    def is_single_entity(self, scope):
        if self._kind in 'spr':
            return True
        return self.limit == 1

    def resolve(self, scope):
        if self is scope.executor.__metadata__:
            return "@s"
        res = '@' + self._kind
        items = []
        for k, v in self.__dict__.items():
            if v is not None and v is not Selector._NotAvailable:
                items.append(v.resolve(scope) if isinstance(v, Resolvable) else f"{k}={v}")
        if len(items) == 0:
            return res
        return f"{res}[{','.join(items)}]"

    def copy(self):
        return type(self)(**self.__dict__)

    def merge(self, other: dict | Self | None):
        """
        将一个新选择器的约束添加到此选择器，返回一个新的选择器
        """
        if other is None:
            return self
        res = self.copy()
        res._update(other if isinstance(other, dict) else other.__dict__)
        return res


class AtA(Selector):
    _kind = 'a'
    _solid = {"type": "minecraft:player"}

class AtE(Selector):
    _kind = 'e'

class AtP(Selector):
    _kind = 'p'
    _solid = {"type": "minecraft:player"}
    _soft = {"sort": "nearest"}

class AtS(Selector):
    _kind = 's'
    _solid = {"limit": 1, "sort": "arbitrary"}

class AtN(Selector):
    _kind = 'n'
    _soft = {"sort": "nearest"}

class AtR(Selector):
    _kind = 'r'
    _solid = {"type": "minecraft:player"}
    _soft = {"sort": "random"}