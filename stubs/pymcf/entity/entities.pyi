from typing import Optional

from pymcf.data import NbtCompound, NbtInt, NbtByte, NbtFloat, NbtString, NbtShort, NbtDouble, NbtIntArray
from pymcf.entity.entity import n_Newable, n_Entity
from pymcf.entity.structure import T_Entity, T_NbtList, T_Item


class __Marker(T_Entity):
    data: NbtCompound

class n_Marker(n_Newable[__Marker]):
    @classmethod
    def entity_type(cls) -> str: ...
    def __init__(self, pos, nbt: Optional[NbtCompound]) -> None: ...


class T_ArmorStandPose(NbtCompound):
    Body: T_NbtList[NbtFloat]
    Head: T_NbtList[NbtFloat]
    LeftArm: T_NbtList[NbtFloat]
    LeftLeg: T_NbtList[NbtFloat]
    RightArm: T_NbtList[NbtFloat]
    RightLeg: T_NbtList[NbtFloat]


class __ArmorStand(T_Entity):
    DisabledSlots: NbtInt
    Invisible: NbtByte
    Marker: NbtByte
    NoBasePlate: NbtByte
    Pose: T_ArmorStandPose
    ShowArms: NbtByte
    Small: NbtByte

class n_ArmorStand(n_Newable[__ArmorStand]):
    @classmethod
    def entity_type(cls) -> str: ...
    def __init__(self, pos, nbt: Optional[NbtCompound]) -> None: ...

class T_PlayerAbilities(NbtCompound):
    walkSpeed: NbtFloat
    flySpeed: NbtFloat
    mayfly: NbtByte
    flying: NbtByte
    invulnerable: NbtByte
    mayBuild: NbtByte
    instabuild: NbtByte

class T_DoublePos3(NbtCompound):
    x: NbtDouble
    y: NbtDouble
    z: NbtDouble

class T_PlayerRootVehicle(NbtCompound):
    Attach: NbtIntArray
    Entity: T_Entity

class T_PlayerRecipeBook(NbtCompound):
    recipes: T_NbtList[NbtString]
    toBeDisplayed: T_NbtList[NbtString]
    isFilteringCraftable: NbtByte
    isGuiOpen: NbtByte
    isFurnaceFilteringCraftable: NbtByte
    isFurnaceGuiOpen: NbtByte

class T_PlayerWardenSpawnTracker(NbtCompound):
    cooldown_ticks: NbtInt
    ticks_since_last_warning: NbtInt
    warning_level: NbtInt

class __Player(T_Entity):
    DataVersion: NbtInt
    playerGameType: NbtInt
    previousPlayerGameType: NbtInt
    Score: NbtInt
    Dimension: NbtString
    SelectedItemSlot: NbtInt
    SelectedItem: T_Item
    SpawnDimension: NbtString
    SpawnX: NbtInt | None
    SpawnY: NbtInt | None
    SpawnZ: NbtInt | None
    SpawnForced: NbtByte
    SleepTimer: NbtShort
    foodLevel: NbtInt
    foodExhaustionLevel: NbtFloat
    foodSaturationLevel: NbtFloat
    foodTickTimer: NbtInt
    XpLevel: NbtInt
    XpP: NbtFloat
    XpTotal: NbtInt
    XpSeed: NbtInt
    Inventory: T_NbtList[T_Item]
    EnderItems: T_NbtList[T_Item]
    abilities: T_PlayerAbilities
    enteredNetherPosition: T_DoublePos3
    RootVehicle: T_PlayerRootVehicle
    ShoulderEntityLeft: T_Entity
    ShoulderEntityRight: T_Entity
    seenCredits: NbtByte
    recipeBook: T_PlayerRecipeBook
    warden_spawn_tracker: T_PlayerWardenSpawnTracker

class n_Player(n_Entity[__Player]):
    @classmethod
    def entity_type(cls) -> str:
        return "minecraft:player"