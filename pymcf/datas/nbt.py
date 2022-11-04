import json
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List, Mapping, Iterable, Tuple

from datas.datas import InGameData


class Nbt(InGameData, ABC):

    def __init__(self):
        self._parent: Optional[Nbt] = None
        self._readonly: bool = True

    @property
    def path(self) -> str:
        if self._parent is None:
            return ""
        else:
            if isinstance(self._parent, NbtCompound):
                p = f"{self._parent.path}.{self._parent._key_of(self)}" if self._parent.path != "" else self._parent._key_of(
                    self)
            elif isinstance(self._parent, NbtList):
                p = f"{self._parent.path}[{self._parent._index_of(self)}]"
            elif isinstance(self._parent, NbtByteArray | NbtIntArray | NbtLongArray):
                p = f"{self._parent.path}[{self._parent._index_of(self)}]"
            else:
                raise TypeError()
            return p

    @abstractmethod
    def serialize(self) -> str:
        ...

    def __str__(self):
        return self.serialize()

    def __repr__(self):
        return self.serialize()

    @staticmethod
    def convert_from(data: Any) -> "Nbt":
        if isinstance(data, Nbt):
            return data
        if isinstance(data, dict):
            return NbtCompound(data)
        if isinstance(data, list):
            return NbtList(data)
        if isinstance(data, str):
            return NbtString(data)
        if isinstance(data, int):
            match data:
                case b if NbtByte._lb <= b <= NbtByte._ub:
                    return NbtByte(b)
                case s if NbtShort._lb <= s <= NbtShort._ub:
                    return NbtShort(s)
                case i if NbtInt._lb <= i <= NbtInt._ub:
                    return NbtInt(i)
                case l if NbtLong._lb <= l <= NbtLong._ub:
                    return NbtLong(l)
                case out_range:
                    raise ValueError(f"could not convert {out_range} to nbt number.")
        if isinstance(data, float):
            if NbtFloat._lb <= data <= NbtFloat._ub:
                return NbtFloat(data)
            else:
                return NbtDouble(data)
        if isinstance(data, tuple):
            match data:
                case ba if all(NbtByte._lb <= b <= NbtByte._ub for b in data):
                    return NbtByteArray(ba)
                case ia if all(NbtInt._lb <= i <= NbtInt._ub for i in data):
                    return NbtIntArray(ia)
                case la if all(NbtLong._lb <= l <= NbtLong._ub for l in data):
                    return NbtLongArray(la)
                case out_range:
                    raise ValueError(f"could not convert {out_range} to nbt number.")

        raise TypeError(f"cannot convert data to nbt item: {data}")


class NbtCompound(Dict[str, Nbt], Nbt):

    def _compatible_to_(self, other):
        return isinstance(other)

    def __update_dict(self, data: Mapping):
        for k, v in data.items():
            k = str(k)
            v = Nbt.convert_from(v)
            v._parent = self
            super(NbtCompound, self).__setitem__(k, v)

    def __init__(self, data: Optional[Dict]):
        super(NbtCompound, self).__init__()
        Nbt.__init__(self)
        if isinstance(data, dict):
            self.__update_dict(data)

    def __str__(self):
        return Nbt.__str__(self)

    def __repr__(self):
        return Nbt.__repr__(self)

    def __getitem__(self, k: str):
        assert isinstance(k, str)
        return super(NbtCompound, self).__getitem__(k)

    def __getattr__(self, k: str):
        return super(NbtCompound, self).__getitem__(k)

    def __setitem__(self, k: str, v: Nbt | Any):
        assert isinstance(k, str)
        v = Nbt.convert_from(v)
        super(NbtCompound, self).__setitem__(k, v)

    def update(self, __m: Mapping, **kwargs) -> None:
        self.__update_dict(__m)
        self.__update_dict(kwargs)

    def clear(self) -> None:
        for v in self.values():
            v._parent = None
        super(NbtCompound, self).clear()

    def _key_of(self, sub: Nbt) -> str:
        for k in self.keys():
            if self[k] is sub:
                return k

    def serialize(self) -> str:
        return '{' + ', '.join(f'"{k}": {v.serialize()}' for k, v in self.items()) + '}'


class NbtList(List[Nbt], Nbt):

    def __extend_list(self, data: Iterable):
        for o in data:
            o = Nbt.convert_from(o)
            o._parent = self
            super(NbtList, self).append(o)

    def __init__(self, data: Optional[List]):
        super().__init__()
        Nbt.__init__(self)
        if isinstance(data, list):
            self.__extend_list(data)

    def __str__(self):
        return Nbt.__str__(self)

    def __repr__(self):
        return Nbt.__repr__(self)

    def __getitem__(self, i: int):
        assert isinstance(i, int)
        return super(NbtList, self).__getitem__(i)

    def __setitem__(self, i: int, o: Nbt | Any):
        assert isinstance(i, int)
        o = Nbt.convert_from(o)
        o._parent = self
        super(NbtList, self).__setitem__(i, o)

    def append(self, __object: Nbt | Any) -> None:
        __object = Nbt.convert_from(__object)
        __object._parent = self
        super(NbtList, self).append(__object)

    def extend(self, __iterable: Iterable[Nbt | Any]) -> None:
        self.__extend_list(__iterable)

    def clear(self) -> None:
        for o in self:
            o._parent = None
        super(NbtList, self).clear()

    def remove(self, __value: Nbt) -> None:
        __value._parent = None
        super(NbtList, self).remove(__value)

    def insert(self, __index: int, __object: Nbt) -> None:
        __object._parent = self
        super(NbtList, self).insert(__index, __object)

    def _index_of(self, o: Nbt) -> int:
        return super(NbtList, self).index(o)

    def serialize(self) -> str:
        return '[' + ', '.join(o.serialize() for o in self) + ']'


class NbtString(Nbt):
    __encoder = json.JSONEncoder()

    def __init__(self, value: Optional[str]):
        super().__init__()
        self.value = value

    def serialize(self) -> str:
        return self.__encoder.encode(self.value)


class NbtByte(Nbt):
    _ub = 2 ** 7 - 1
    _lb = - 2 ** 7

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def serialize(self) -> str:
        return str(self.value) + 'b'


class NbtShort(Nbt):
    _ub = 2 ** 15 - 1
    _lb = - 2 ** 15

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def serialize(self) -> str:
        return str(self.value) + 's'


class NbtInt(Nbt):
    _ub = 2 ** 31 - 1
    _lb = - 2 ** 31

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def serialize(self) -> str:
        return str(self.value)


class NbtLong(Nbt):
    _ub = 2 ** 63 - 1
    _lb = - 2 ** 63

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def serialize(self) -> str:
        return str(self.value) + 'L'


class NbtFloat(Nbt):
    _lb = - 2. ** 128
    _ub = 2. ** 128

    def __init__(self, value: Optional[float]):
        super().__init__()
        self.value = value

    def serialize(self) -> str:
        return str(self.value) + 'f'


class NbtDouble(Nbt):

    def __init__(self, value: Optional[float]):
        super().__init__()
        self.value = value

    def serialize(self) -> str:
        return str(self.value) + 'd'


class NbtByteArray(Tuple[NbtByte], Nbt):

    def __new__(cls, data: Optional[Tuple[int]]):
        self = super(NbtByteArray, cls).__new__(cls, (NbtByte(i) for i in data))
        return self

    def __init__(self, _):
        for o in self:
            o._parent = self
        Nbt.__init__(self)

    def __str__(self):
        return Nbt.__str__(self)

    def __repr__(self):
        return Nbt.__repr__(self)

    def _index_of(self, o: Nbt) -> int:
        return super().index(o)

    def serialize(self) -> str:
        return '[B; ' + ', '.join(str(b.value) for b in self) + ']'


class NbtIntArray(Tuple[NbtInt], Nbt):

    def __new__(cls, data: Optional[Tuple[int]]):
        self = super(NbtIntArray, cls).__new__(cls, (NbtInt(i) for i in data))
        return self

    def __init__(self, _):
        for o in self:
            o._parent = self
        Nbt.__init__(self)

    def __str__(self):
        return Nbt.__str__(self)

    def __repr__(self):
        return Nbt.__repr__(self)

    def _index_of(self, o: Nbt) -> int:
        return super().index(o)

    def serialize(self) -> str:
        return '[I; ' + ', '.join(str(b.value) for b in self) + ']'


class NbtLongArray(Tuple[NbtLong], Nbt):

    def __new__(cls, data: Optional[Tuple[int]]):
        self = super(NbtLongArray, cls).__new__(cls, (NbtLong(i) for i in data))
        return self

    def __init__(self, _):
        for o in self:
            o._parent = self
        Nbt.__init__(self)

    def __str__(self):
        return Nbt.__str__(self)

    def __repr__(self):
        return Nbt.__repr__(self)

    def _index_of(self, o: Nbt) -> int:
        return super().index(o)

    def serialize(self) -> str:
        return '[L; ' + ', '.join(str(b.value) for b in self) + ']'


class NbtContainer(ABC):

    def __init__(self, structure: NbtCompound):
        self._nbt = structure
