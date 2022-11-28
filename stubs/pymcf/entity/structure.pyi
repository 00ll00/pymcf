from typing import Union, TypeVar

from pymcf.data.nbt import NbtByte as NbtByte, NbtCompound as NbtCompound, NbtDouble as NbtDouble, NbtFloat as NbtFloat, NbtInt as NbtInt, NbtIntArray as NbtIntArray, NbtList as NbtList, NbtLong as NbtLong, NbtShort as NbtShort, NbtString as NbtString

_T_Nbt = TypeVar("_T_Nbt", bound=NbtCompound)

class T_NbtList(NbtList):
    def __getitem__(self, item) -> _T_Nbt: ...
    def __setitem__(self, key: int, value): ...

class T_Entity(NbtCompound):
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
    Passengers: T_NbtList['T_Entity']
    PortalCooldown: NbtInt
    Pos: T_NbtList[NbtDouble]
    Rotation: T_NbtList[NbtFloat]
    Silent: NbtByte
    Tags: T_NbtList[NbtString]
    UUID: NbtIntArray

class T_Effect(NbtCompound):
    Ambient: NbtByte
    Amplifier: NbtByte
    Duration: NbtInt
    HiddenEffect: T_Effect
    Id: NbtByte
    ShowIcon: NbtByte
    ShowParticles: NbtByte

class T_Enchant(NbtCompound):
    id: NbtString
    lvl: NbtShort

class T_AttributeModifier(NbtCompound):
    AttributeName: NbtString
    Name: NbtString
    Slot: NbtString
    Operation: NbtInt
    Amount: NbtDouble
    UUID: NbtIntArray

class T_ItemDisplay(NbtCompound):
    color: NbtInt
    Name: NbtString
    Lore: T_NbtList[NbtString]

class T_SkullTexture(NbtCompound):
    Signature: NbtString
    Value: NbtString

class T_SkullOwner(NbtCompound):
    Id: NbtIntArray
    Name: NbtString
    Properties: T_NbtList[T_SkullTexture]

class T_FireWorkExplosion(NbtCompound):
    Flicker: NbtByte
    Trail: NbtByte
    Type: NbtByte
    Colors: NbtIntArray
    FadeColors: NbtIntArray

class T_Firework(NbtCompound):
    Flight: NbtByte
    Explosions: T_NbtList[T_FireWorkExplosion]

class T_MapDecoration(NbtCompound):
    id: NbtString
    type: NbtByte
    x: NbtDouble
    y: NbtDouble
    rot: NbtDouble

class T_SuspiciousStewEffect(NbtCompound):
    EffectId: NbtByte
    EffectDuration: NbtInt

class T_NbtBlockPos3(NbtCompound):
    X: NbtInt
    Y: NbtInt
    Z: NbtInt

class T_ItemTags(NbtCompound):
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
    LodestonePos: T_NbtBlockPos3
    Items: T_NbtList['T_Item']

class T_Item(NbtCompound):
    Count: NbtByte
    id: NbtString
    tag: T_ItemTags

class T_CreatureAttributeModifier(NbtCompound):
    Amount: NbtDouble
    Name: NbtString
    Operation: NbtInt
    UUID: NbtIntArray

class T_CreatureAttribute(NbtCompound):
    Base: NbtDouble
    Modifiers: T_NbtList[T_CreatureAttributeModifier]
    Name: NbtString

class T_CreatureBrain(NbtCompound):
    memories: NbtCompound

class T_Creature(T_Entity):
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
    Leash: Union[NbtIntArray, T_NbtBlockPos3]
    LeftHanded: NbtByte
    NoAI: NbtByte
    PersistenceRequired: NbtByte
    SleepingX: NbtInt
    SleepingY: NbtInt
    SleepingZ: NbtInt
    Team: NbtString
    TicksFrozen: NbtInt

class T_CanBreed(NbtCompound):
    Age: NbtInt
    ForcedAge: NbtInt
    InLove: NbtInt
    LoveCause: NbtIntArray

class T_CanAnger(NbtCompound):
    AngerTime: NbtInt
    AngryAt: NbtIntArray

class T_CanTame(NbtCompound):
    Owner: NbtIntArray
    Sitting: NbtByte

class T_Zombie(NbtCompound):
    CanBreakDoors: NbtByte
    DrownedConversionTime: NbtInt
    InWaterTime: NbtInt
    IsBaby: NbtByte

class T_Projectile(NbtCompound):
    HasBeenShot: NbtByte
    LeftOwner: NbtByte
    Owner: NbtIntArray

class T_FireBall(NbtCompound):
    power: T_NbtList[NbtDouble]
    Motion: T_NbtList[NbtDouble]

class T_CanRaid(NbtCompound):
    CanJoinRaid: NbtByte
    HasRaidGoal: NbtByte
    PatrolLeader: NbtByte
    Patrolling: NbtByte
    PatrolTarget: T_NbtBlockPos3
    RaidId: NbtInt
    Wave: NbtInt

class T_Horse(NbtCompound):
    ArmorItem: T_Item
    Bred: NbtByte
    EatingHaystack: NbtByte
    Owner: NbtIntArray
    SaddleItem: T_Item
    Tame: NbtByte
    Temper: NbtInt

class T_ArrowInBlockState(NbtCompound):
    Name: NbtString
    Properties: NbtCompound

class T_Arrow(NbtCompound):
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
