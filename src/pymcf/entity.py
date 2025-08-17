from abc import ABC, ABCMeta
from typing import Self

from pymcf.mcfunction import mcfunction
from pymcf.nbtlib import NbtCompound

from .ast_ import Raw, Constructor
from .data import Entity
from .mc.commands import AtA, AtE, Summon, WorldPos, Selector


class Player(Entity):
    __entity_type__ = "minecraft:player"
    __base_selector__ = AtA()


class _SummonableMeta(ABCMeta):

    def __new__(mcls, name, bases, attrs, entity_type=None, **kwargs):
        cls = super().__new__(mcls, name, bases, attrs)
        if entity_type is not None:
            cls.__base_selector__ = AtE(type=entity_type)
            cls.__entity_type__ = entity_type
        return cls


class _Summonable(Entity, metaclass=_SummonableMeta):
    """
   可召唤实体基类

   entity = Summonable() 可以召唤一个实体，返回的 entity 仅用于在当前代码块临时定位实体。

   若需要长期定位此实体，需要及时为其添加额外的标识。
   """

    __base_selector__: Selector
    __entity_type__: str

    @classmethod
    @mcfunction.inline
    def summon(cls, _pos: str = "~ ~ ~", _nbt: NbtCompound = None):
        _scope = Constructor.current_constr().scope
        _var_tag = _scope.new_local_entity_tag()
        self = super().__new__(cls, _ref=cls.__base_selector__.merge(Selector(tag=_var_tag, limit=1)))

        if _nbt is None:
            _nbt = NbtCompound()

        _tags = _nbt.find("Tags", NbtList())
        assert isinstance(_tags, NbtList)
        _tags.append(_var_tag)

        _nbt["Tags"] = _tags

        f'tag @e[tag={_var_tag}] remove {_var_tag}'
        f'summon {cls.__entity_type__} {_pos} {_nbt}'

        self.init()

        return self

    def init(self, *args, **kwargs):
        """
        完成实体初始化。
        """


class Marker(_Summonable, entity_type='minecraft:marker'):
    ...

class TextDisplay(_Summonable, entity_type='minecraft:text_display'):
    ...

class BlockDisplay(_Summonable, entity_type='minecraft:block_display'):
    ...

class ItemDisplay(_Summonable, entity_type='minecraft:item_display'):
    ...
