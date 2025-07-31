"""
Wrapper of nbtlib
"""

from nbtlib import Byte as NbtByte, ByteArray as NbtByteArray, Short as NbtShort, Int as NbtInt, \
    IntArray as NbtIntArray, \
    Long as NbtLong, LongArray as NbtLongArray, Float as NbtFloat, Double as NbtDouble, Compound as NbtCompound, \
    List as NbtList, \
    Array as NbtArray, String as NbtString

from nbtlib import Path as _NbtPath

from nbtlib.schema import CompoundSchema as NbtCompoundSchema

NbtData = NbtByte | NbtByteArray | NbtShort | NbtInt | NbtIntArray | NbtLong | NbtLongArray | NbtFloat | \
          NbtDouble | NbtCompound | NbtList | NbtArray | NbtString

from nbtlib import parse_nbt, serialize_tag

__all__ = [
    "NbtByte", "NbtByteArray", "NbtShort", "NbtInt", "NbtIntArray", "NbtLong", "NbtLongArray", "NbtFloat", "NbtDouble",
    "NbtCompound", "NbtList", "NbtArray", "NbtString", "NbtData", "NbtCompoundSchema"
]
