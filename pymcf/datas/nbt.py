import json
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List, Mapping, Iterable, Tuple, TypeVar, Generic

from pymcf import MCVer
from pymcf.datas.datas import InGameData
from pymcf.datas.score import Fixed
from pymcf.jsontext import IJsonText, JsonText, JsonTextComponent
from pymcf.operations import Operation
from pymcf.util import staticproperty, lazy


class NbtCopyOp(Operation):

    def __init__(self, target: "Nbt", source: "Nbt"):
        self.target = target
        self.source = source
        super(NbtCopyOp, self).__init__()

    def gen_code(self, mcver: MCVer) -> str:
        return f"data modify {self.target} set from {self.source}"


class NbtSetScoreOp(Operation):

    def __init__(self, target: "Nbt", score, dtype: str = "int", scale: float = 1):
        self.target = target
        self.score = score
        self.dtype = dtype
        self.scale = scale
        super().__init__()

    def gen_code(self, mcver: MCVer) -> str:
        return f"execute store result {self.target} {self.dtype} {self.scale} run scoreboard players get {self.score}"


class NbtData(ABC):
    """
    base type of all nbt data.
    """

    def __init__(self):
        self._parent: Optional[NbtData] = None
        self._readonly: bool = True

    @property
    def _path(self) -> str:
        if self._parent is None:
            return ""
        else:
            if isinstance(self._parent, NbtCompound):
                p = f"{self._parent._path}.{self._parent._key_of(self)}" if self._parent._path != "" else self._parent._key_of(
                    self)
            elif isinstance(self._parent, NbtList):
                p = f"{self._parent._path}[{self._parent._index_of(self)}]"
            elif isinstance(self._parent, NbtByteArray | NbtIntArray | NbtLongArray):
                p = f"{self._parent._path}[{self._parent._index_of(self)}]"
            else:
                raise TypeError()
            return p

    @abstractmethod
    def _serialize(self) -> str:
        ...

    as_byte: "NbtData"
    as_short: "NbtData"
    as_int: "NbtData"
    as_long: "NbtData"
    as_float: "NbtData"
    as_double: "NbtData"
    json: JsonText

    def __str__(self):
        return self._serialize()

    def __repr__(self):
        return self._serialize()

    @staticmethod
    def convert_from(data: Any) -> "NbtData":
        if isinstance(data, NbtData):
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


class NbtCompound(Dict[str, NbtData], NbtData):

    def __update_dict(self, data: Mapping):
        for k, v in data.items():
            k = str(k)
            v = NbtData.convert_from(v)
            v._parent = self
            super(NbtCompound, self).__setitem__(k, v)

    def __init__(self, data: Optional[Mapping] = None):
        super(NbtCompound, self).__init__()
        NbtData.__init__(self)
        if isinstance(data, Mapping):
            self.__update_dict(data)

    def __str__(self):
        return NbtData.__str__(self)

    def __repr__(self):
        return NbtData.__repr__(self)

    def __getitem__(self, k: str) -> NbtData:
        assert isinstance(k, str)
        return super(NbtCompound, self).__getitem__(k)

    def __setitem__(self, k: str, v: NbtData | Any):
        assert isinstance(k, str)
        v = NbtData.convert_from(v)
        super(NbtCompound, self).__setitem__(k, v)

    def update(self, __m: Mapping, **kwargs) -> None:
        self.__update_dict(__m)
        self.__update_dict(kwargs)

    def clear(self) -> None:
        for v in self.values():
            v._parent = None
        super(NbtCompound, self).clear()

    def _key_of(self, sub: NbtData) -> str:
        for k in self.keys():
            if self[k] is sub:
                return k

    def _serialize(self) -> str:
        return '{' + ', '.join(f'"{k}": {v._serialize()}' for k, v in self.items()) + '}'


class NbtList(List[NbtData], NbtData):

    def __extend_list(self, data: Iterable):
        for o in data:
            o = NbtData.convert_from(o)
            o._parent = self
            super(NbtList, self).append(o)

    def __init__(self, data: Optional[List] = None):
        super().__init__()
        NbtData.__init__(self)
        if isinstance(data, list):
            self.__extend_list(data)

    def __str__(self):
        return NbtData.__str__(self)

    def __repr__(self):
        return NbtData.__repr__(self)

    def __getitem__(self, i: int):
        assert isinstance(i, int)
        return super(NbtList, self).__getitem__(i)

    def __setitem__(self, i: int, o: NbtData | Any):
        assert isinstance(i, int)
        o = NbtData.convert_from(o)
        o._parent = self
        super(NbtList, self).__setitem__(i, o)

    def append(self, __object: NbtData | Any) -> None:
        __object = NbtData.convert_from(__object)
        __object._parent = self
        super(NbtList, self).append(__object)

    def extend(self, __iterable: Iterable[NbtData | Any]) -> None:
        self.__extend_list(__iterable)

    def clear(self) -> None:
        for o in self:
            o._parent = None
        super(NbtList, self).clear()

    def remove(self, __value: NbtData) -> None:
        __value._parent = None
        super(NbtList, self).remove(__value)

    def insert(self, __index: int, __object: NbtData) -> None:
        __object._parent = self
        super(NbtList, self).insert(__index, __object)

    def _index_of(self, o: NbtData) -> int:
        return super(NbtList, self).index(o)

    def _serialize(self) -> str:
        return '[' + ', '.join(o._serialize() for o in self) + ']'


class NbtString(NbtData):
    __encoder = json.JSONEncoder()

    def __init__(self, value: Optional[str]):
        super().__init__()
        self.value = value

    def _serialize(self) -> str:
        return self.__encoder.encode(self.value)


class NbtByte(NbtData):
    _ub = 2 ** 7 - 1
    _lb = - 2 ** 7

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def _serialize(self) -> str:
        return str(self.value) + 'b'


class NbtShort(NbtData):
    _ub = 2 ** 15 - 1
    _lb = - 2 ** 15

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def _serialize(self) -> str:
        return str(self.value) + 's'


class NbtInt(NbtData):
    _ub = 2 ** 31 - 1
    _lb = - 2 ** 31

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def _serialize(self) -> str:
        return str(self.value)


class NbtLong(NbtData):
    _ub = 2 ** 63 - 1
    _lb = - 2 ** 63

    def __init__(self, value: Optional[int]):
        super().__init__()
        self.value = value

    def _serialize(self) -> str:
        return str(self.value) + 'L'


class NbtFloat(NbtData):
    _lb = - 2. ** 128
    _ub = 2. ** 128

    def __init__(self, value: Optional[float]):
        super().__init__()
        self.value = value

    def _serialize(self) -> str:
        return str(self.value) + 'f'


class NbtDouble(NbtData):

    def __init__(self, value: Optional[float]):
        super().__init__()
        self.value = value

    def _serialize(self) -> str:
        return str(self.value) + 'd'


class NbtByteArray(Tuple[NbtByte], NbtData):

    def __new__(cls, data: Optional[Tuple[int]]):
        self = super(NbtByteArray, cls).__new__(cls, (NbtByte(i) for i in data))
        return self

    def __init__(self, _):
        for o in self:
            o._parent = self
        NbtData.__init__(self)

    def __str__(self):
        return NbtData.__str__(self)

    def __repr__(self):
        return NbtData.__repr__(self)

    def _index_of(self, o: NbtData) -> int:
        return super().index(o)

    def _serialize(self) -> str:
        return '[B; ' + ', '.join(str(b.value) for b in self) + ']'


class NbtIntArray(Tuple[NbtInt], NbtData):

    def __new__(cls, data: Optional[Tuple[int]]):
        self = super(NbtIntArray, cls).__new__(cls, (NbtInt(i) for i in data))
        return self

    def __init__(self, _):
        for o in self:
            o._parent = self
        NbtData.__init__(self)

    def __str__(self):
        return NbtData.__str__(self)

    def __repr__(self):
        return NbtData.__repr__(self)

    def _index_of(self, o: NbtData) -> int:
        return super().index(o)

    def _serialize(self) -> str:
        return '[I; ' + ', '.join(str(b.value) for b in self) + ']'


class NbtLongArray(Tuple[NbtLong], NbtData):

    def __new__(cls, data: Optional[Tuple[int]]):
        self = super(NbtLongArray, cls).__new__(cls, (NbtLong(i) for i in data))
        return self

    def __init__(self, _):
        for o in self:
            o._parent = self
        NbtData.__init__(self)

    def __str__(self):
        return NbtData.__str__(self)

    def __repr__(self):
        return NbtData.__repr__(self)

    def _index_of(self, o: NbtData) -> int:
        return super().index(o)

    def _serialize(self) -> str:
        return '[L; ' + ', '.join(str(b.value) for b in self) + ']'


class Nbt(InGameData, IJsonText):
    _sys_tmp_id = 0

    def __init__(self, owner: Optional["NbtContainer"] = None, path: str = ""):
        if owner is not None:
            self._owner = owner
            self._path = path if not path.startswith('.') else path[1:]
            self._type = "int"
        else:
            Nbt._sys_tmp_id += 1
            self._owner = NbtContainer.SYS
            self._path = f"temp.var{Nbt._sys_tmp_id}"

    @property
    def as_byte(self):
        self._type = "byte"
        return self

    @property
    def as_short(self):
        self._type = "short"
        return self

    @property
    def as_int(self):
        self._type = "int"
        return self

    @property
    def as_long(self):
        self._type = "long"
        return self

    @property
    def as_float(self):
        self._type = "float"
        return self

    @property
    def as_double(self):
        self._type = "double"
        return self

    @property
    def json(self) -> JsonText:
        data = {"nbt": self._path, self._owner._get_type_(): self._owner._get_id_()}
        return JsonTextComponent(data)

    def __getitem__(self, item):
        if type(item) in {int, NbtCompound}:
            return Nbt(self._owner, self._path + f"[{item}]")
        if isinstance(item, Mapping):
            return Nbt(self._owner, self._path + f"[{NbtCompound(item)}]")
        if type(item) is str:
            return Nbt(self._owner, self._path + f".{item}")

    def __getattr__(self, item):
        if item.startswith('_'):
            return self.__dict__[item]
        else:
            return Nbt(self._owner, self._path + f".{item}")

    def __str__(self):
        return f"{self._owner._nbt_container_()} {self._path}"

    def __setitem__(self, key, value):
        pass  # assignments wrapped in codes

    def __setattr__(self, key: str, value):
        if key.startswith('_'):
            self.__dict__[key] = value
        else:
            pass  # assignments wrapped in codes

    def _set_value(self, value):
        from pymcf.datas.score import Score
        if isinstance(value, Score):
            NbtSetScoreOp(self, value, dtype=self._type)
        elif isinstance(value, Fixed):
            NbtSetScoreOp(self, value, dtype=self._type, scale=1/value.scale)
        else:
            raise ValueError(f"cannot set {type(value)} to nbt")

    def _transfer_to_(self, other):
        NbtCopyOp(other, self)

    def _new_from_(self) -> "Nbt":
        return Nbt()


_T_Nbt = TypeVar("_T_Nbt", bound=NbtData)


class NbtContainer(Generic[_T_Nbt], ABC):

    @property
    def nbt(self) -> _T_Nbt:
        # noinspection PyTypeChecker
        return Nbt(owner=self)

    @abstractmethod
    def _get_type_(self) -> str:
        ...

    @abstractmethod
    def _get_id_(self) -> str:
        ...

    def _nbt_container_(self) -> str:
        return f"{self._get_type_()} {self._get_id_()}"

    def __str__(self):
        return self._nbt_container_()

    # noinspection PyMethodParameters
    @staticproperty
    @lazy
    def SYS():
        return StorageNbtContainer("sys")


class EntityNbtContainer(NbtContainer[_T_Nbt]):

    def __init__(self, identifier):
        super(EntityNbtContainer, self).__init__()
        self._identifier = identifier

    def _get_type_(self) -> str:
        return "entity"

    def _get_id_(self):
        return str(self._identifier)


class StorageNbtContainer(NbtContainer[_T_Nbt]):

    def __init__(self, name):
        super(StorageNbtContainer, self).__init__()
        self._name = name

    def _get_type_(self) -> str:
        return "storage"

    def _get_id_(self):
        from pymcf import Project
        return f"{Project.namespace}:{self._name}"


class BlockNbtContainer(NbtContainer[_T_Nbt]):

    def __init__(self, pos):
        super(BlockNbtContainer, self).__init__()
        self._pos = pos

    def _get_type_(self) -> str:
        return "block"

    def _get_id_(self):
        return f"{self._pos[0]} {self._pos[1]} {self._pos[2]}"
