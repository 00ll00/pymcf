from abc import ABC
from collections import defaultdict
from typing import Generic, TypeVar

from pymcf.operations import raw
from pymcf.datas.datas import InGameIter
from pymcf.datas.selector import Selector, Self


class Entity:
    pass


class ScoreEntity(Entity):
    group_count = defaultdict(int)

    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def new_dummy(group: str = "dummy"):
        ScoreEntity.group_count[group] += 1
        return ScoreEntity(f'${group}_' + str(ScoreEntity.group_count[group]))


class SelectableEntity:

    def __init__(self):
        self.selector: Selector = Self()


E = TypeVar("E", bound=Entity)


class Entities(InGameIter[E], Generic[E], ABC):

    def __init__(self):
        super(Entities, self).__init__()


class Marker(Entity):  # TODO

    def __init__(self, x, y, z, tag: str):
        self.tag = tag
        raw(f"""summon minecraft:marker {x} {y} {z} {{"Tags": [{tag}]}}""")

    def tp(self, x, y, z):
        raw(f"""tp {self} {x} {y} {z}""")

    def kill(self):
        raw(f"""kill {self}""")

    def __str__(self):
        return f"@e[tag={self.tag}, limit=1]"
