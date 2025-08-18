"""
Wrapper of nbtlib
"""

from nbtlib import Byte as _Byte, ByteArray as _ByteArray, Short as _Short, Int as _Int, \
    IntArray as _IntArray, \
    Long as _Long, LongArray as _LongArray, Float as _Float, Double as _Double, Compound as _Compound, \
    List as _List, Array as _Array, String as _String, Base as _Base, End as _End

from nbtlib import Path as _NbtPath

from nbtlib.schema import CompoundSchema as NbtCompoundSchema
from pymcf.ast_ import Resolvable


class _NbtResolvable(_Base, Resolvable):

    def resolve(self, scope):
        return self.snbt(compact=True,quote="'")


class NbtByte(_Byte, _NbtResolvable):
    pass
class NbtByteArray(_ByteArray, _NbtResolvable):
    pass
class NbtShort(_Short, _NbtResolvable):
    pass
class NbtInt(_Int, _NbtResolvable):
    pass
class NbtIntArray(_IntArray, _NbtResolvable):
    pass
class NbtLong(_Long, _NbtResolvable):
    pass
class NbtLongArray(_LongArray, _NbtResolvable):
    pass
class NbtFloat(_Float, _NbtResolvable):
    pass
class NbtDouble(_Double, _NbtResolvable):
    pass
class NbtCompound(_Compound, _NbtResolvable):
    pass
class NbtList(_List, _NbtResolvable):
    def __class_getitem__(cls, item):
        if item is _End:
            return NbtList
        try:
            return cls.variants[item]
        except KeyError:
            variant = type(
                f"NbtList[{item.__name__}]", (NbtList,), {"__slots__": (), "subtype": item}
            )
            cls.variants[item] = variant
            return variant
class NbtArray(_Array, _NbtResolvable):
    pass
class NbtString(_String, _NbtResolvable):
    pass


NbtData = NbtByte | NbtByteArray | NbtShort | NbtInt | NbtIntArray | NbtLong | NbtLongArray | NbtFloat | \
          NbtDouble | NbtCompound | NbtList | NbtArray | NbtString

from nbtlib import parse_nbt, serialize_tag

__all__ = [
    "NbtByte", "NbtByteArray", "NbtShort", "NbtInt", "NbtIntArray", "NbtLong", "NbtLongArray", "NbtFloat", "NbtDouble",
    "NbtCompound", "NbtList", "NbtArray", "NbtString", "NbtData", "NbtCompoundSchema"
]
