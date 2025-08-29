from abc import abstractmethod

import nbtlib
from nbtlib import serialize_tag

from ...nbtlib import _NbtPath, NbtData

from .core import Resolvable, Command, EntityRef, WorldPos


class NbtPath(_NbtPath, Resolvable):
    # TODO 特殊字符路径转义，合法性检验
    def resolve(self, scope):
        return str(self)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self)

class NbtStorable(Resolvable):

    @abstractmethod
    def as_text(self, scope):
        ...

class EntityReference(NbtStorable):

    def __init__(self, target):
        assert isinstance(target, EntityRef)
        self.target = target

    def resolve(self, scope):
        # assert self.target.is_single_entity(scope)  # TODO
        return 'entity %s' % self.target.resolve(scope)

    def as_text(self, scope):
        assert self.target.is_single_entity(scope)
        return {'entity': self.target.resolve(scope)}

class BlockReference(NbtStorable):

    def __init__(self, pos):
        assert isinstance(pos, WorldPos) and pos.block_pos
        self.pos = pos

    def resolve(self, scope):
        return 'block %s' % self.pos.resolve(scope)

    def as_text(self, scope):
        return {'block': self.pos.resolve(scope)}

class Storage(NbtStorable):

    def __init__(self, nsname: str):
        self.nsname = nsname

    def resolve(self, scope):
        return f'storage {self.nsname}'

    def as_text(self, scope):
        return {'storage': self.nsname}

class NbtRef(Resolvable):

    def __init__(self, target: NbtStorable, path: NbtPath):
        assert isinstance(target, NbtStorable)
        assert isinstance(path, NbtPath)
        self.target = target
        self.path = path

    def resolve(self, scope):
        return f"{self.target.resolve(scope)} {self.path.resolve(scope)}"


class MacroRef(NbtRef):

    def __init__(self, target: NbtStorable, path: NbtPath):
        assert isinstance(target, Storage)  # TODO 确保是 namespace:__sys__
        assert isinstance(path, NbtPath)  # TODO 确保其位于 var 路径下
        assert isinstance(tuple(path)[-1], nbtlib.NamedKey)
        self.var_name = tuple(path)[-1].key
        super().__init__(target, path)

    def resolve(self, scope):
        return f"$({self.var_name})"

# class GlobalNBT(NBTStorable):
#
#     def __init__(self, namespace):
#         self.namespace = namespace
#
#     def proxy(self, scope):
#         return scope.global_nbt(self.namespace)
#
#     def resolve(self, scope):
#         return self.proxy(scope).resolve(scope)
#
#     def as_text(self, scope):
#         return self.proxy(scope).as_text(scope)

class DataGet(Command):

    def __init__(self, target, path, scale=1):
        assert isinstance(target, NbtStorable)
        assert isinstance(scale, (int, float)) or scale is None
        self.target = target
        self.path = path
        self.scale = None if scale is None else \
                     int(scale) if scale == int(scale) else scale

    def resolve(self, scope):
        scale = ' %s' % self.scale if self.scale is not None else ''
        return 'data get %s %s%s' % (self.target.resolve(scope),
                                     self.path.resolve(scope), scale)

class DataMerge(Command):

    def __init__(self, ref, nbt):
        assert isinstance(ref, NbtStorable)
        self.ref = ref
        self.nbt = nbt

    def resolve(self, scope):
        return 'data merge %s %s' % (self.ref.resolve(scope),
                                     self.nbt.resolve(scope))

class DataModify(Command):

    @abstractmethod
    def init(self, *args): ...

    def __init__(self, ref, path, action, *rest):
        assert isinstance(ref, NbtStorable)
        self.ref = ref
        self.path = path
        self.action = action
        self.init(*rest)

    def resolve(self, scope):
        return 'data modify %s %s %s' % (
            self.ref.resolve(scope), self.path.resolve(scope), self.action)

class DataModifyValue(DataModify):

    def init(self, val):
        assert isinstance(val, NbtData)
        self.val = val

    def resolve(self, scope):
        return f'{super().resolve(scope)} value {serialize_tag(self.val,compact=True,quote="'")}'

class DataModifyFrom(DataModify):

    def init(self, ref, path):
        assert isinstance(ref, NbtStorable)
        self.fromref = ref
        self.frompath = path

    def resolve(self, scope):
        return '%s from %s %s' % (super().resolve(scope),
                                  self.fromref.resolve(scope), self.frompath.resolve(scope))

# class DataModifyStack(DataModifyValue):
#
#     def __init__(self, index, key, action, value, namespace=None):
#         super().__init__(GlobalNBT(namespace), StackPath(index, key), action,
#                          value)

class DataRemove(Command):

    def __init__(self, ref, path):
        assert isinstance(ref, NbtStorable)
        self.ref = ref
        self.path = path

    def resolve(self, scope):
        return 'data remove %s %s' % (self.ref.resolve(scope),
                                      self.path.resolve(scope))
