from .core import Resolvable, Command, EntityRef, WorldPos

class NbtPath(Resolvable):

    def __init__(self, path):
        self.path = path

    def subpath(self, childpath):
        # TODO path validation
        return self.__class__(self.path + childpath)

    def resolve(self, scope, fmt=None):
        return self.path

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.path == other.path

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.path)

class Path(NbtPath):

    def resolve(self, scope, fmt=None):
        return scope.custom_nbt_path(self.path)

class SubPath(Path):

    def __init__(self, subpath=None, subkey=None):
        assert subkey is None or subpath is not None
        sub = subpath if subpath is not None else ''
        sub += '.' + subkey if subkey else ''
        super().__init__(self.name + sub)
        self.subpart = subpath
        self.keypart = subkey

    def subpath(self, childpath):
        # Don't use our constructor
        return Path(self.path).subpath(childpath)

class ArrayPath(SubPath):

    def __init__(self, index=None, key=None):
        super().__init__('[%d]' % index if index is not None else None, key)
        self.index = index

class StackPath(ArrayPath):
    name = 'stack'

def StackFrame(index):
    class StackFramePath(ArrayPath):
        name = 'stack[%d].stack' % (-index - 1)
    return StackFramePath

StackFrameHead = StackFrame(0)

class GlobalPath(SubPath):
    name = 'global'

    def __init__(self, name=None, key=None):
        super().__init__('.' + name if name is not None else None, key)

class NBTStorable(Resolvable):
    pass

class EntityReference(NBTStorable):

    def __init__(self, target):
        assert isinstance(target, EntityRef)
        self.target = target

    def resolve(self, scope, fmt=None):
        assert self.target.is_single_entity(scope)
        return 'entity %s' % self.target.resolve(scope, None)

    def as_text(self, scope):
        assert self.target.is_single_entity(scope)
        return {'entity': self.target.resolve(scope, None)}

class BlockReference(NBTStorable):

    def __init__(self, pos):
        assert isinstance(pos, WorldPos) and pos.block_pos
        self.pos = pos

    def resolve(self, scope, fmt=None):
        return 'block %s' % self.pos.resolve(scope, None)

    def as_text(self, scope):
        return {'block': self.pos.resolve(scope, None)}

class Storage(NBTStorable):

    def __init__(self, namespace=None):
        self.namespace = namespace

    def resolve(self, scope, fmt=None):
        return 'storage %s' % scope.storage(self.namespace)

    def as_text(self, scope):
        return {'storage': scope.storage(self.namespace)}

class NbtRef(Resolvable):

    def __init__(self, target: NBTStorable, path: NbtPath):
        assert isinstance(target, NBTStorable)
        assert isinstance(path, NbtPath)
        self.target = target
        self.path = path

    def resolve(self, scope, fmt=None):
        return f"{self.target.resolve(scope, None)} {self.path.resolve(scope, None)}"


class GlobalNBT(NBTStorable):

    def __init__(self, namespace):
        self.namespace = namespace

    def proxy(self, scope):
        return scope.global_nbt(self.namespace)

    def resolve(self, scope, fmt=None):
        return self.proxy(scope).resolve(scope, None)

    def as_text(self, scope):
        return self.proxy(scope).as_text(scope)

class DataGet(Command):

    def __init__(self, target, path, scale=1):
        assert isinstance(target, NBTStorable)
        assert isinstance(scale, (int, float)) or scale is None
        self.target = target
        self.path = path
        self.scale = None if scale is None else \
                     int(scale) if scale == int(scale) else scale

    def resolve(self, scope, fmt=None):
        scale = ' %s' % self.scale if self.scale is not None else ''
        return 'data get %s %s%s' % (self.target.resolve(scope, None),
                                     self.path.resolve(scope, None), scale)

class DataMerge(Command):

    def __init__(self, ref, nbt):
        assert isinstance(ref, NBTStorable)
        self.ref = ref
        self.nbt = nbt

    def resolve(self, scope, fmt=None):
        return 'data merge %s %s' % (self.ref.resolve(scope, None),
                                     self.nbt.resolve(scope, None))

class DataModify(Command):

    def __init__(self, ref, path, action, *rest):
        assert isinstance(ref, NBTStorable)
        self.ref = ref
        self.path = path
        self.action = action
        self.init(*rest)

    def resolve(self, scope, fmt=None):
        return 'data modify %s %s %s' % (
            self.ref.resolve(scope, None), self.path.resolve(scope, None), self.action)

class DataModifyValue(DataModify):

    def init(self, val):
        self.val = val

    def resolve(self, scope, fmt=None):
        return '%s value %s' % (super().resolve(scope, None), self.val.resolve(scope, None))

class DataModifyFrom(DataModify):

    def init(self, ref, path):
        assert isinstance(ref, NBTStorable)
        self.fromref = ref
        self.frompath = path

    def resolve(self, scope, fmt=None):
        return '%s from %s %s' % (super().resolve(scope, None),
                                  self.fromref.resolve(scope, None), self.frompath.resolve(scope, None))

class DataModifyStack(DataModifyValue):

    def __init__(self, index, key, action, value, namespace=None):
        super().__init__(GlobalNBT(namespace), StackPath(index, key), action,
                         value)

class DataRemove(Command):

    def __init__(self, ref, path):
        assert isinstance(ref, NBTStorable)
        self.ref = ref
        self.path = path

    def resolve(self, scope, fmt=None):
        return 'data remove %s %s' % (self.ref.resolve(scope, None),
                                      self.path.resolve(scope, None))
