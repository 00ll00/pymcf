from abc import ABC, ABCMeta
from typing import Self

from pymcf.mcfunction import mcfunction
from pymcf.nbtlib import NbtCompound, NbtString
from pymcf.project import Project

from .ast_ import Raw, Constructor
from .data import Entity, NbtList
from .mc.commands import AtA, AtE, Summon, WorldPos, Selector


class Player(Entity):
    __entity_type__ = "minecraft:player"
    __base_selector__ = AtA()


def get_cls_tag(cls, namespace: str = None) -> str:
    if namespace is None:
        namespace = Project.instance().name
    return  f'{namespace}.{cls.__module__}.{cls.__name__}'


class _SummonableMeta(ABCMeta):

    def __new__(mcls, name, bases, attrs, entity_type=None, **kwargs):
        cls = super().__new__(mcls, name, bases, attrs)
        if entity_type is not None:  # 定义了实体类型的类以类型作为基础选择器
            cls.__base_selector__ = AtE(type=entity_type)
            cls.__entity_type__ = entity_type
        elif bases[0] is not Entity:  # 排除 _Summonable
            cls.__base_selector__ = AtE(tag=get_cls_tag(cls))
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
    def summon(cls, _pos: str = "~ ~ ~", _tag: str | set[str] = None, _nbt: NbtCompound = None):
        _scope = Constructor.current_constr().scope
        _var_tag = _scope.new_local_entity_tag()
        self = cls.select(tag=_var_tag, limit=1)

        if _nbt is None:
            _nbt = NbtCompound()

        if _tag is None:
            _tag = set()
        elif isinstance(_tag, str):
            _tag = {_tag}
        _tag.add(_var_tag)

        # 收集类型 tag
        for _base in cls.mro():
            if issubclass(_base, _Summonable) and "__base_selector__" in _base.__dict__:
                _selector = _base.__base_selector__
                if _selector.tag is not None:
                    for _t in _selector.tag.tags:
                        _tag.add(_t)

        _nbt_tags = _nbt.find("Tags", NbtList[NbtString]())
        assert isinstance(_nbt_tags, NbtList[NbtString])

        for _t in _tag:
            _nbt_tags.append(_t)

        _nbt["Tags"] = _nbt_tags

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
