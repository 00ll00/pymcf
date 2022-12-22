from typing import Optional

from pymcf.data import NbtCompound
from pymcf.entity.entity import n_Newable, n_Entity


class n_Marker(n_Newable):

    @classmethod
    def entity_type(cls) -> str:
        return "minecraft:marker"

    def __init__(self, pos, nbt: Optional[NbtCompound]):
        super().__init__(pos, nbt)


class n_ArmorStand(n_Newable):

    @classmethod
    def entity_type(cls) -> str:
        return "minecraft:armor_stand"

    def __init__(self, pos, nbt: Optional[NbtCompound]):
        super().__init__(pos, nbt)


class n_Player(n_Entity):

    @classmethod
    def entity_type(cls) -> str:
        return "minecraft:player"


del Optional, NbtCompound, n_Newable
