from typing import Union, TypeVar, Generic, TypedDict, List, Tuple, Dict, Any, TypeshedSelf

from pymcf.data.nbt import NbtByte as NbtByte, NbtCompound as NbtCompound, NbtDouble as NbtDouble, NbtFloat as NbtFloat, \
    NbtInt as NbtInt, NbtIntArray as NbtIntArray, NbtList as NbtList, NbtLong as NbtLong, NbtShort as NbtShort, \
    NbtString as NbtString, NbtData as NbtData

_T_Nbt = TypeVar("_T_Nbt", bound=NbtData)

class T_NbtList(NbtList, Generic[_T_Nbt]):
    def __getitem__(self, item) -> _T_Nbt: ...
    def __setitem__(self, key: int, value): ...

_T_NbtList = List
_T_NbtString = str
_T_NbtInt = int
_T_NbtByte = Union[int, bool]
_T_NbtShort = int
_T_NbtLong = int
_T_NbtFloat = float
_T_NbtDouble = float
_T_NbtCompound = Dict[str, Any]
_T_NbtIntArray = Tuple[int, ...]

__RecurRef = Any

A = TypedDict("A", fields={"bbbb": B})
B = TypedDict("B", fields={"aaaa": int})


_T_Entity = TypedDict(
    "_T_Entity",
    fields={
        "Air": _T_NbtShort,
        "CustomName": _T_NbtString,
        "CustomNameVisible": _T_NbtByte,
        "FallDistance": _T_NbtFloat,
        "Fire": _T_NbtShort,
        "Glowing": _T_NbtByte,
        "HasVisualFire": _T_NbtByte,
        "id": _T_NbtString,
        "Invulnerable": _T_NbtByte,
        "Motion": _T_NbtList[_T_NbtDouble],
        "NoGravity": _T_NbtByte,
        "OnGround": _T_NbtByte,
        "Passengers": _T_NbtList[__RecurRef],
        "PortalCooldown": _T_NbtInt,
        "Pos": _T_NbtList[_T_NbtDouble],
        "Rotation": _T_NbtList[_T_NbtFloat],
        "Silent": _T_NbtByte,
        "Tags": _T_NbtList[_T_NbtString],
        "UUID": _T_NbtIntArray,
    },
    total=False
)

class T_Entity(NbtCompound):
    def __init__(self, data: _T_Entity): ...
    Air: NbtShort
    CustomName: NbtString
    CustomNameVisible: NbtByte
    FallDistance: NbtFloat
    Fire: NbtShort
    Glowing: NbtByte
    HasVisualFire: NbtByte
    id: NbtString
    Invulnerable: NbtByte
    Motion: T_NbtList[NbtDouble]
    NoGravity: NbtByte
    OnGround: NbtByte
    Passengers: T_NbtList[T_Entity]
    PortalCooldown: NbtInt
    Pos: T_NbtList[NbtDouble]
    Rotation: T_NbtList[NbtFloat]
    Silent: NbtByte
    Tags: T_NbtList[NbtString]
    UUID: NbtIntArray

_T_Effect = TypedDict(
    "_T_Effect",
    fields={
        "Ambient": _T_NbtByte,
        "Amplifier": _T_NbtByte,
        "Duration": _T_NbtInt,
        "HiddenEffect": __RecurRef,
        "Id": _T_NbtByte,
        "ShowIcon": _T_NbtByte,
        "ShowParticles": _T_NbtByte,
    },
    total=False
)

class T_Effect(NbtCompound):
    def __init__(self, data: _T_Effect): ...
    Ambient: NbtByte
    Amplifier: NbtByte
    Duration: NbtInt
    HiddenEffect: T_Effect
    Id: NbtByte
    ShowIcon: NbtByte
    ShowParticles: NbtByte

_T_Enchant = TypedDict(
    "_T_Enchant",
    fields={
        "id": _T_NbtString,
        "lvl": _T_NbtShort
    },
    total=False
)

class T_Enchant(NbtCompound):
    def __init__(self, data: _T_Enchant): ...
    id: NbtString
    lvl: NbtShort

_T_AttributeModifier = TypedDict(
    "_T_AttributeModifier",
    fields={
        "AttributeName": _T_NbtString,
        "Name": _T_NbtString,
        "Slot": _T_NbtString,
        "Operation": _T_NbtInt,
        "Amount": _T_NbtDouble,
        "UUID": _T_NbtIntArray,
    },
    total=False
)

class T_AttributeModifier(NbtCompound):
    def __init__(self, data: _T_AttributeModifier): ...
    AttributeName: NbtString
    Name: NbtString
    Slot: NbtString
    Operation: NbtInt
    Amount: NbtDouble
    UUID: NbtIntArray

_T_ItemDisplay = TypedDict(
    "_T_ItemDisplay",
    fields={
        "color": _T_NbtInt,
        "Name": _T_NbtString,
        "Lore": _T_NbtList[_T_NbtString],
    },
    total=False
)

class T_ItemDisplay(NbtCompound):
    def __init__(self, data: _T_ItemDisplay): ...
    color: NbtInt
    Name: NbtString
    Lore: T_NbtList[NbtString]

_T_SkullTexture = TypedDict(
    "_T_SkullTexture",
    fields={
        "Signature": _T_NbtString,
        "Value": _T_NbtString
    },
    total=False
)

class T_SkullTexture(NbtCompound):
    def __init__(self, data: _T_SkullTexture): ...
    Signature: NbtString
    Value: NbtString

_T_SkullOwner = TypedDict(
    "_T_SkullOwner",
    fields={
        "Id": _T_NbtIntArray,
        "Name": _T_NbtString,
        "Properties": _T_NbtList[_T_SkullTexture]
    },
    total=False
)

class T_SkullOwner(NbtCompound):
    def __init__(self, data: _T_SkullOwner): ...
    Id: NbtIntArray
    Name: NbtString
    Properties: T_NbtList[T_SkullTexture]

_T_FireWorkExplosion = TypedDict(
    "_T_FireWorkExplosion",
    fields={
        "Flicker": _T_NbtByte,
        "Trail": _T_NbtByte,
        "Type": _T_NbtByte,
        "Colors": _T_NbtIntArray,
        "FadeColors": _T_NbtIntArray,
    },
    total=False
)

class T_FireWorkExplosion(NbtCompound):
    def __init__(self, data: _T_FireWorkExplosion): ...
    Flicker: NbtByte
    Trail: NbtByte
    Type: NbtByte
    Colors: NbtIntArray
    FadeColors: NbtIntArray

_T_Firework = TypedDict(
    "_T_Firework",
    fields={
        "Flight": _T_NbtByte,
        "Explosions": _T_NbtList[_T_FireWorkExplosion],
    },
    total=False
)

class T_Firework(NbtCompound):
    def __init__(self, data: _T_Firework): ...
    Flight: NbtByte
    Explosions: T_NbtList[T_FireWorkExplosion]

_T_MapDecoration = TypedDict(
    "_T_MapDecoration",
    fields={
        "id": _T_NbtString,
        "type": _T_NbtByte,
        "x": _T_NbtDouble,
        "y": _T_NbtDouble,
        "rot": _T_NbtDouble,
    },
    total=False
)

class T_MapDecoration(NbtCompound):
    def __init__(self, data: _T_MapDecoration): ...
    id: NbtString
    type: NbtByte
    x: NbtDouble
    y: NbtDouble
    rot: NbtDouble

_T_SuspiciousStewEffect = TypedDict(
    "_T_SuspiciousStewEffect",
    fields={
        "EffectId": _T_NbtByte,
        "EffectDuration": _T_NbtInt,
    },
    total=False
)

class T_SuspiciousStewEffect(NbtCompound):
    def __init__(self, data: _T_SuspiciousStewEffect): ...
    EffectId: NbtByte
    EffectDuration: NbtInt

_T_IntPos3 = TypedDict(
    "_T_IntPos3",
    fields={
        "X": _T_NbtInt,
        "Y": _T_NbtInt,
        "Z": _T_NbtInt,
    },
    total=False
)

class T_IntPos3(NbtCompound):
    def __init__(self, data: _T_IntPos3): ...
    X: NbtInt
    Y: NbtInt
    Z: NbtInt

_T_ItemTags = TypedDict(
    "_T_ItemTags",
    fields={
        "Damage": _T_NbtInt,
        "Unbreakable": _T_NbtByte,
        "CanDestroy": _T_NbtList[_T_NbtString],
        "CustomModelData": _T_NbtInt,
        "CanPlaceOn": _T_NbtList[_T_NbtString],
        "BlockEntityTag": _T_Entity,
        "BlockStateTag": _T_NbtCompound,
        "Enchantments": _T_NbtList[_T_Enchant],
        "StoredEnchantments": _T_NbtList[_T_Enchant],
        "RepairCost": _T_NbtInt,
        "AttributeModifiers": _T_NbtList[_T_AttributeModifier],
        "CustomPotionEffects": _T_NbtList[_T_Effect],
        "Potion": _T_NbtString,
        "CustomPotionColor": _T_NbtInt,
        "Charged": _T_NbtByte,
        "ChargedProjectiles": _T_NbtList[__RecurRef],
        "display": _T_ItemDisplay,
        "HideFlags": _T_NbtInt,
        "resolved": _T_NbtByte,
        "generation": _T_NbtInt,
        "author": _T_NbtString,
        "title": _T_NbtString,
        "pages": _T_NbtList[_T_NbtString],
        "SkullOwner": Union[_T_NbtString, _T_SkullOwner],
        "Fireworks": _T_NbtList[_T_Firework],
        "EntityTag": _T_Entity,
        "BucketVariantTag": _T_NbtInt,
        "map": _T_NbtInt,
        "map_scale_direction": _T_NbtInt,
        "Decorations": _T_NbtList[_T_MapDecoration],
        "Effects": _T_NbtList[_T_SuspiciousStewEffect],
        "DebugProperty": _T_NbtCompound,
        "LodestoneTracked": _T_NbtByte,
        "LodestoneDimension": _T_NbtString,
        "LodestonePos": _T_IntPos3,
        "Items": _T_NbtList[__RecurRef],
    },
    total=False,
)

class T_ItemTags(NbtCompound):
    def __init__(self, data: _T_ItemTags): ...
    Damage: NbtInt
    Unbreakable: NbtByte
    CanDestroy: T_NbtList[NbtString]
    CustomModelData: NbtInt
    CanPlaceOn: T_NbtList[NbtString]
    BlockEntityTag: T_Entity
    BlockStateTag: NbtCompound
    Enchantments: T_NbtList[T_Enchant]
    StoredEnchantments: T_NbtList[T_Enchant]
    RepairCost: NbtInt
    AttributeModifiers: T_NbtList[T_AttributeModifier]
    CustomPotionEffects: T_NbtList[T_Effect]
    Potion: NbtString
    CustomPotionColor: NbtInt
    Charged: NbtByte
    ChargedProjectiles: T_NbtList['T_Item']
    display: T_ItemDisplay
    HideFlags: NbtInt
    resolved: NbtByte
    generation: NbtInt
    author: NbtString
    title: NbtString
    pages: T_NbtList[NbtString]
    SkullOwner: Union[NbtString, T_SkullOwner]
    Fireworks: T_NbtList[T_Firework]
    EntityTag: T_Entity
    BucketVariantTag: NbtInt
    map: NbtInt
    map_scale_direction: NbtInt
    Decorations: T_NbtList[T_MapDecoration]
    Effects: T_NbtList[T_SuspiciousStewEffect]
    DebugProperty: NbtCompound
    LodestoneTracked: NbtByte
    LodestoneDimension: NbtString
    LodestonePos: T_IntPos3
    Items: T_NbtList['T_Item']

_T_Item = TypedDict(
    "_T_Item",
    fields={
        "Count": _T_NbtByte,
        "id": _T_NbtString,
        "tag": _T_ItemTags,
    },
    total=False
)

class T_Item(NbtCompound):
    def __init__(self, data: _T_Item): ...
    Count: NbtByte
    id: NbtString
    tag: T_ItemTags

_T_CreatureAttributeModifier = TypedDict(
    "_T_CreatureAttributeModifier",
    fields={
        "Amount": _T_NbtDouble,
        "Name": _T_NbtString,
        "Operation": _T_NbtInt,
        "UUID": _T_NbtIntArray,
    },
    total=False
)

class T_CreatureAttributeModifier(NbtCompound):
    def __init__(self, data: _T_CreatureAttributeModifier): ...
    Amount: NbtDouble
    Name: NbtString
    Operation: NbtInt
    UUID: NbtIntArray

_T_CreatureAttribute = TypedDict(
    "_T_CreatureAttribute",
    fields={
        "Base": _T_NbtDouble,
        "Modifiers": _T_NbtList[_T_CreatureAttributeModifier],
        "Name": _T_NbtString,
    },
    total=False
)

class T_CreatureAttribute(NbtCompound):
    def __init__(self, data: _T_CreatureAttribute): ...
    Base: NbtDouble
    Modifiers: T_NbtList[T_CreatureAttributeModifier]
    Name: NbtString

_T_CreatureBrain = TypedDict(
    "_T_CreatureBrain",
    fields={
        "memories": _T_NbtCompound,
    },
    total=False
)

class T_CreatureBrain(NbtCompound):
    def __init__(self, data: _T_CreatureBrain): ...
    memories: NbtCompound

_T_Creature = TypedDict(
    "_T_Creature",
    fields={
        "AbsorptionAmount": _T_NbtFloat,
        "ActiveEffects": _T_NbtList[_T_Effect],
        "ArmorDropChances": _T_NbtList[_T_NbtFloat],
        "ArmorItems": _T_NbtList[_T_Item],
        "Attributes": _T_NbtList[_T_CreatureAttribute],
        "Brain": _T_CreatureBrain,
        "CanPickUpLoot": _T_NbtByte,
        "DeathLootTable": _T_NbtString,
        "DeathLootTableSeed": _T_NbtLong,
        "DeathTime": _T_NbtShort,
        "FallFlying": _T_NbtByte,
        "Health": _T_NbtFloat,
        "HurtByTimestamp": _T_NbtInt,
        "HurtTime": _T_NbtShort,
        "HandDropChances": _T_NbtList[_T_NbtFloat],
        "HandItems": _T_NbtList[_T_Item],
        "Leash": Union[_T_NbtIntArray, _T_IntPos3],
        "LeftHanded": _T_NbtByte,
        "NoAI": _T_NbtByte,
        "PersistenceRequired": _T_NbtByte,
        "SleepingX": _T_NbtInt,
        "SleepingY": _T_NbtInt,
        "SleepingZ": _T_NbtInt,
        "Team": _T_NbtString,
        "TicksFrozen": _T_NbtInt,
    },
    total=False
)

class T_Creature(T_Entity):
    def __init__(self, data: _T_Creature): ...
    AbsorptionAmount: NbtFloat
    ActiveEffects: T_NbtList[T_Effect]
    ArmorDropChances: T_NbtList[NbtFloat]
    ArmorItems: T_NbtList[T_Item]
    Attributes: T_NbtList[T_CreatureAttribute]
    Brain: T_CreatureBrain
    CanPickUpLoot: NbtByte
    DeathLootTable: NbtString
    DeathLootTableSeed: NbtLong
    DeathTime: NbtShort
    FallFlying: NbtByte
    Health: NbtFloat
    HurtByTimestamp: NbtInt
    HurtTime: NbtShort
    HandDropChances: T_NbtList[NbtFloat]
    HandItems: T_NbtList[T_Item]
    Leash: Union[NbtIntArray, T_IntPos3]
    LeftHanded: NbtByte
    NoAI: NbtByte
    PersistenceRequired: NbtByte
    SleepingX: NbtInt
    SleepingY: NbtInt
    SleepingZ: NbtInt
    Team: NbtString
    TicksFrozen: NbtInt

_T_CanBreed = TypedDict(
    "_T_CanBreed",
    fields={
        "Age": _T_NbtInt,
        "ForcedAge": _T_NbtInt,
        "InLove": _T_NbtInt,
        "LoveCause": _T_NbtIntArray,
    }
)

class T_CanBreed(NbtCompound):
    def __init__(self, data: _T_CanBreed): ...
    Age: NbtInt
    ForcedAge: NbtInt
    InLove: NbtInt
    LoveCause: NbtIntArray

_T_CanAnger = TypedDict(
    "_T_CanAnger",
    fields={
        "AngerTime": _T_NbtInt,
        "AngryAt": _T_NbtIntArray,
    },
    total=False
)

class T_CanAnger(NbtCompound):
    def __init__(self, data: _T_CanAnger): ...
    AngerTime: NbtInt
    AngryAt: NbtIntArray

_T_CanTame = TypedDict(
    "_T_CanTame",
    fields={
        "Owner": _T_NbtIntArray,
        "Sitting": _T_NbtByte,
    },
    total=False
)

class T_CanTame(NbtCompound):
    def __init__(self, data: _T_CanTame): ...
    Owner: NbtIntArray
    Sitting: NbtByte

_T_Zombie = TypedDict(
    "_T_Zombie",
    fields={
        "CanBreakDoors": _T_NbtByte,
        "DrownedConversionTime": _T_NbtInt,
        "InWaterTime": _T_NbtInt,
        "IsBaby": _T_NbtByte,
    },
    total=False
)

class T_Zombie(NbtCompound):
    def __init__(self, data: _T_Zombie): ...
    CanBreakDoors: NbtByte
    DrownedConversionTime: NbtInt
    InWaterTime: NbtInt
    IsBaby: NbtByte

_T_Projectile = TypedDict(
    "_T_Projectile",
    fields={
        "HasBeenShot": _T_NbtByte,
        "LeftOwner": _T_NbtByte,
        "Owner": _T_NbtIntArray,
    },
    total=False
)

class T_Projectile(NbtCompound):
    def __init__(self, data: _T_Projectile): ...
    HasBeenShot: NbtByte
    LeftOwner: NbtByte
    Owner: NbtIntArray

_T_FireBall = TypedDict(
    "_T_FireBall",
    fields={
        "power": _T_NbtList[_T_NbtDouble],
        "Motion": _T_NbtList[_T_NbtDouble],
    },
    total=False
)

class T_FireBall(NbtCompound):
    def __init__(self, data: _T_FireBall): ...
    power: T_NbtList[NbtDouble]
    Motion: T_NbtList[NbtDouble]

_T_CanRaid = TypedDict(
    "_T_CanRaid",
    fields={
        "CanJoinRaid": _T_NbtByte,
        "HasRaidGoal": _T_NbtByte,
        "PatrolLeader": _T_NbtByte,
        "Patrolling": _T_NbtByte,
        "PatrolTarget": _T_IntPos3,
        "RaidId": _T_NbtInt,
        "Wave": _T_NbtInt,
    },
    total=False
)

class T_CanRaid(NbtCompound):
    def __init__(self, data: _T_CanRaid): ...
    CanJoinRaid: NbtByte
    HasRaidGoal: NbtByte
    PatrolLeader: NbtByte
    Patrolling: NbtByte
    PatrolTarget: T_IntPos3
    RaidId: NbtInt
    Wave: NbtInt

_T_Horse = TypedDict(
    "_T_Horse",
    fields={
        "ArmorItem": _T_Item,
        "Bred": _T_NbtByte,
        "EatingHaystack": _T_NbtByte,
        "Owner": _T_NbtIntArray,
        "SaddleItem": _T_Item,
        "Tame": _T_NbtByte,
        "Temper": _T_NbtInt,
    },
    total=False
)

class T_Horse(NbtCompound):
    def __init__(self, data: _T_Horse): ...
    ArmorItem: T_Item
    Bred: NbtByte
    EatingHaystack: NbtByte
    Owner: NbtIntArray
    SaddleItem: T_Item
    Tame: NbtByte
    Temper: NbtInt

_T_ArrowInBlockState = TypedDict(
    "_T_ArrowInBlockState",
    fields={
        "Name": _T_NbtString,
        "Properties": _T_NbtCompound
    },
    total=False
)

class T_ArrowInBlockState(NbtCompound):
    def __init__(self, data: _T_ArrowInBlockState): ...
    Name: NbtString
    Properties: NbtCompound

_T_Arrow = TypedDict(
    "_T_Arrow",
    fields={
        "crit": _T_NbtByte,
        "damage": _T_NbtDouble,
        "inBlockState": _T_ArrowInBlockState,
        "inGround": _T_NbtByte,
        "life": _T_NbtShort,
        "pickup": _T_NbtByte,
        "PierceLevel": _T_NbtByte,
        "shake": _T_NbtByte,
        "ShotFromCrossbow": _T_NbtByte,
        "SoundEvent": _T_NbtString,
    },
    total=False
)

class T_Arrow(NbtCompound):
    def __init__(self, data: _T_Arrow): ...
    crit: NbtByte
    damage: NbtDouble
    inBlockState: T_ArrowInBlockState
    inGround: NbtByte
    life: NbtShort
    pickup: NbtByte
    PierceLevel: NbtByte
    shake: NbtByte
    ShotFromCrossbow: NbtByte
    SoundEvent: NbtString
