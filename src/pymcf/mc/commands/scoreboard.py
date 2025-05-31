import json

from .core import Command, Resolvable, EntityRef, GlobalEntity

class Scoreboard(Command):

    allows_negative = False

    def __init__(self, varref, value):
        assert isinstance(varref, ScoreRef)
        assert isinstance(value, int)
        assert self.allows_negative or value >= 0
        self.var = varref
        self.value = value

    def resolve(self, scope):
        return 'scoreboard players %s %s %d' % (
            self.op, self.var.resolve(scope), self.value)

class SetConst(Scoreboard):
    op = 'set'
    allows_negative = True

class AddConst(Scoreboard):
    op = 'add'

class RemConst(Scoreboard):
    op = 'remove'

class GetValue(Command):

    def __init__(self, scoreref):
        assert isinstance(scoreref, ScoreRef)
        self.ref = scoreref

    def resolve(self, scope):
        return 'scoreboard players get %s' % self.ref.resolve(scope)

class ResetValue(Command):

    def __init__(self, scoreref):
        assert isinstance(scoreref, ScoreRef)
        self.ref = scoreref

    def resolve(self, scope):
        return 'scoreboard players reset %s' % self.ref.resolve(scope)

class Operation(Command):
    def __init__(self, left, right):
        assert isinstance(left, ScoreRef)
        assert isinstance(right, ScoreRef)
        self.left = left
        self.right = right

    def resolve(self, scope):
        return 'scoreboard players operation %s %s %s' % (
            self.left.resolve(scope), self.op, self.right.resolve(scope))

class OpAssign(Operation): op = '='
class OpAdd(Operation): op = '+='
class OpSub(Operation): op = '-='
class OpMul(Operation): op = '*='
class OpDiv(Operation): op = '/='
class OpMod(Operation): op = '%='
class OpIfLt(Operation): op = '<'
class OpIfGt(Operation): op = '>'
class OpSwap(Operation): op = '><'

class ObjectiveRef(Resolvable):

    def __init__(self, name):
        assert type(name) == str
        self.objective = name

    def resolve(self, scope):
        return self.objective

class ScoreboardAdd(Command):

    def __init__(self, ref: ObjectiveRef, criteria: str, display_name=None):
        from . import TextComponent
        assert isinstance(ref, ObjectiveRef)
        assert isinstance(criteria, str)
        assert isinstance(display_name, None | str | TextComponent)
        self.ref = ref
        self.criteria = criteria
        self.display_name = display_name

    def resolve(self, scope):
        from . import TextComponent
        res = f"scoreboard objectives add {self.ref.resolve(scope)} {self.criteria}"
        if self.display_name is not None:
            if isinstance(self.display_name, str):
                res += f" {self.display_name!r}"
            elif isinstance(self.display_name, TextComponent):
                res += " " + self.display_name.resolve(scope)
        return res

class ScoreRef(Resolvable):

    def __init__(self, target, objective):
        assert isinstance(target, EntityRef)
        assert isinstance(objective, ObjectiveRef)
        self.target = target
        self.objective = objective

    def resolve(self, scope):
        return '%s %s' % (self.target.resolve(scope),
                          self.objective.resolve(scope))

class Var(ScoreRef):
    def __init__(self, nameref, namespace=None):
        super().__init__(GlobalEntity(namespace), ObjectiveRef(nameref))
