from abc import ABC, ABCMeta
from typing import Self

from .ast_ import Raw, Constructor
from .data import Entity
from .mc.commands import AtA, AtE, Summon, WorldPos, Selector


class Player(Entity):

    __base_selector__ = AtA()

    def __init__(self):
        raise TypeError(f'Player 不能被生成，使用 select 获取实例。')


class _SummonableMeta(ABCMeta):

    def __new__(mcls, name, bases, attrs, _type=None, **kwargs):
        cls = super().__new__(mcls, name, bases, attrs)
        if _type is not None:
            cls.__base_selector__ = AtE(type=_type)
            cls.__entity_type__ = _type
        return cls

class _Summonable(Entity, metaclass=_SummonableMeta):

    __base_selector__: Selector

    @classmethod
    def summon(cls, pos=None, data=None, *, as_var=False) -> Self | None:
        if data is None:
            data = {}
        # TODO summon 是否应当定义在这里
        Raw(Summon(cls.__entity_type__, pos, data))
        if as_var:
            return cls.__new__(cls, _ref=cls.__base_selector__.merge(
                {"tag": Constructor.current_constr().scope.new_local_tag()}))
        else:
            return None



class Marker(_Summonable, _type='minecraft:marker'):
    ...