from typing import Generic, TypeVar

from pymcf.datas.nbt import NbtCompound, NbtShort, NbtString, NbtByte, NbtFloat, \
    NbtDouble, NbtInt, NbtIntArray, NbtList, NbtLong

_T_Nbt = TypeVar("_T_Nbt", bound=NbtCompound)


class _T_NbtList(NbtList, Generic[_T_Nbt]):

    def __getitem__(self, item) -> _T_Nbt:
        ...

    def __setitem__(self, key: int, value):
        ...


class _T_Entity(NbtCompound):
    Air: NbtShort
    CustomName: NbtString
    CustomNameVisible: NbtByte
    FallDistance: NbtFloat
    Fire: NbtShort
    Glowing: NbtByte
    HasVisualFire: NbtByte
    id: NbtString
    Invulnerable: NbtByte
    Motion: _T_NbtList[NbtDouble]
    NoGravity: NbtByte
    OnGround: NbtByte
    Passengers: _T_NbtList["_T_Entity"]
    PortalCooldown: NbtInt
    Pos: _T_NbtList[NbtDouble]
    Rotation: _T_NbtList[NbtFloat]
    Silent: NbtByte
    Tags: _T_NbtList[NbtString]
    UUID: NbtIntArray


class _T_Effect(NbtCompound):
    Ambient: NbtByte
    Amplifier: NbtByte
    Duration: NbtInt
    HiddenEffect: "_T_Effect"
    Id: NbtByte
    ShowIcon: NbtByte
    ShowParticles: NbtByte


class _T_Enchant(NbtCompound):
    id: NbtString
    lvl: NbtShort


class _T_AttributeModifier(NbtCompound):
    AttributeName: NbtString
    Name: NbtString
    Slot: NbtString
    Operation: NbtInt
    Amount: NbtDouble
    UUID: NbtIntArray


class _T_ItemDisplay(NbtCompound):
    color: NbtInt
    Name: NbtString
    Lore: _T_NbtList[NbtString]


class _T_SkullTexture(NbtCompound):
    Signature: NbtString
    Value: NbtString


class _T_SkullOwner(NbtCompound):
    Id: NbtIntArray
    Name: NbtString
    Properties: _T_NbtList[_T_SkullTexture]


class _T_FireWorkExplosion(NbtCompound):
    Flicker: NbtByte
    Trail: NbtByte
    Type: NbtByte
    Colors: NbtIntArray
    FadeColors: NbtIntArray


class _T_Firework(NbtCompound):
    Flight: NbtByte
    Explosions: _T_NbtList[_T_FireWorkExplosion]


class _T_MapDecoration(NbtCompound):
    id: NbtString
    type: NbtByte
    x: NbtDouble
    y: NbtDouble
    rot: NbtDouble


class _T_SuspiciousStewEffect(NbtCompound):
    EffectId: NbtByte
    EffectDuration: NbtInt


class _T_NbtBlockPos3(NbtCompound):
    X: NbtInt
    Y: NbtInt
    Z: NbtInt


class _T_ItemTags(NbtCompound):
    Damage: NbtInt
    Unbreakable: NbtByte
    CanDestroy: _T_NbtList[NbtString]
    CustomModelData: NbtInt

    # block tag
    CanPlaceOn: _T_NbtList[NbtString]
    BlockEntityTag: _T_Entity
    BlockStateTag: NbtCompound

    # enchant
    Enchantments: _T_NbtList[_T_Enchant]
    StoredEnchantments: _T_NbtList[_T_Enchant]
    RepairCost: NbtInt

    # attribute modifiers
    AttributeModifiers: _T_NbtList[_T_AttributeModifier]

    # potion
    CustomPotionEffects: _T_NbtList[_T_Effect]
    Potion: NbtString
    CustomPotionColor: NbtInt

    # crossbow
    Charged: NbtByte
    ChargedProjectiles: _T_NbtList["_T_Item"]

    # display
    display: _T_ItemDisplay
    HideFlags: NbtInt

    # written book
    resolved: NbtByte
    generation: NbtInt
    author: NbtString
    title: NbtString
    pages: _T_NbtList[NbtString]

    # player head
    SkullOwner: NbtString | _T_SkullOwner

    # firework star
    Fireworks: _T_NbtList[_T_Firework]

    # spawn egg
    EntityTag: _T_Entity

    # fish bucket
    BucketVariantTag: NbtInt

    # map
    map: NbtInt
    map_scale_direction: NbtInt
    Decorations: _T_NbtList[_T_MapDecoration]
    display: NbtInt

    # suspicious stew
    Effects: _T_NbtList[_T_SuspiciousStewEffect]

    # debug stick
    DebugProperty: NbtCompound

    # compass
    LodestoneTracked: NbtByte
    LodestoneDimension: NbtString
    LodestonePos: _T_NbtBlockPos3

    # bundle
    Items: _T_NbtList["_T_Item"]


class _T_Item(NbtCompound):
    Count: NbtByte
    id: NbtString
    tag: _T_ItemTags


class _T_CreatureAttributeModifier(NbtCompound):
    Amount: NbtDouble
    Name: NbtString
    Operation: NbtInt
    UUID: NbtIntArray


class _T_CreatureAttribute(NbtCompound):
    Base: NbtDouble
    Modifiers: _T_NbtList[_T_CreatureAttributeModifier]
    Name: NbtString


class _T_CreatureBrain(NbtCompound):
    memories: NbtCompound


class _T_Creature(_T_Entity):
    AbsorptionAmount: NbtFloat
    ActiveEffects: _T_NbtList[_T_Effect]
    ArmorDropChances: _T_NbtList[NbtFloat]
    ArmorItems: _T_NbtList[_T_Item]
    Attributes: _T_NbtList[_T_CreatureAttribute]
    Brain: _T_CreatureBrain
    CanPickUpLoot: NbtByte
    DeathLootTable: NbtString
    DeathLootTableSeed: NbtLong
    DeathTime: NbtShort
    FallFlying: NbtByte
    Health: NbtFloat
    HurtByTimestamp: NbtInt
    HurtTime: NbtShort
    HandDropChances: _T_NbtList[NbtFloat]
    HandItems: _T_NbtList[_T_Item]
    Leash: NbtIntArray | _T_NbtBlockPos3
    LeftHanded: NbtByte
    NoAI: NbtByte
    PersistenceRequired: NbtByte
    SleepingX: NbtInt
    SleepingY: NbtInt
    SleepingZ: NbtInt
    Team: NbtString
    TicksFrozen: NbtInt


class _T_CanBreed(NbtCompound):
    Age: NbtInt
    ForcedAge: NbtInt
    InLove: NbtInt
    LoveCause: NbtIntArray


class _T_CanAnger(NbtCompound):
    AngerTime: NbtInt
    AngryAt: NbtIntArray


class _T_CanTame(NbtCompound):
    Owner: NbtIntArray
    Sitting: NbtByte


class _T_Zombie(NbtCompound):
    CanBreakDoors: NbtByte
    DrownedConversionTime: NbtInt
    InWaterTime: NbtInt
    IsBaby: NbtByte


class _T_Projectile(NbtCompound):
    HasBeenShot: NbtByte
    LeftOwner: NbtByte
    Owner: NbtIntArray


class _T_FireBall(NbtCompound):
    power: _T_NbtList[NbtDouble]
    Motion: _T_NbtList[NbtDouble]


class _T_CanRaid(NbtCompound):
    CanJoinRaid: NbtByte
    HasRaidGoal: NbtByte
    PatrolLeader: NbtByte
    Patrolling: NbtByte
    PatrolTarget: _T_NbtBlockPos3
    RaidId: NbtInt
    Wave: NbtInt


class _T_Horse(NbtCompound):
    ArmorItem: _T_Item
    Bred: NbtByte
    EatingHaystack: NbtByte
    Owner: NbtIntArray
    SaddleItem: _T_Item
    Tame: NbtByte
    Temper: NbtInt


class _T_ArrowInBlockState(NbtCompound):
    Name: NbtString
    Properties: NbtCompound


class _T_Arrow(NbtCompound):
    crit: NbtByte
    damage: NbtDouble
    inBlockState: _T_ArrowInBlockState
    inGround: NbtByte
    life: NbtShort
    pickup: NbtByte
    PierceLevel: NbtByte
    shake: NbtByte
    ShotFromCrossbow: NbtByte
    SoundEvent: NbtString


