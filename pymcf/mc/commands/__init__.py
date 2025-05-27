from .core import *
from .execute import *
from .nbt import *
from .scoreboard import *
from .selector import *
from .text import *

class Cmd(Command):
    def __init__(self, cmd):
        self.command = cmd

    def resolve(self, scope, fmt=None):
        cmd = self.command
        # This should be refactored eventually
        # Support set_scoreboard_tracking() and text_set_click_run()
        # in the C compiler
        import re
        while True:
            m = re.search('\\$(func|entity_local):(.+?)\\$', cmd)
            if not m:
                break
            if m.group(1) == 'func':
                replace = scope.function_name(NSName('sub_' + m.group(2)))
            else:
                replace = scope.objective(m.group(2))
            cmd = cmd[:m.start()] + replace + cmd[m.end():]
        return cmd

class Function(Command):

    def __init__(self, token):
        self.token = token

    def resolve(self, scope, fmt=None):
        return 'function %s' % scope.function_nsname(self.token)

class FunctionTag(Command):

    def __init__(self, tag_name):
        assert isinstance(tag_name, NSName)
        self._name = tag_name

    def resolve(self, scope, fmt=None):
        return 'function #' + scope.func_tag_name(self._name)

class Teleport(Command):

    def __init__(self, target, *more):
        assert isinstance(target, EntityRef)
        self.args = [target]
        self.args.extend(more)

    def resolve(self, scope, fmt=None):
        return 'tp %s' % ' '.join(a.resolve(scope, None) for a in self.args)

class Clone(Command):

    def __init__(self, src0, src1, dest):
        self.src0 = src0
        self.src1 = src1
        self.dest = dest

    def resolve(self, scope, fmt=None):
        return 'clone %s %s %s' % (self.src0.resolve(scope, None),
                                   self.src1.resolve(scope, None),
                                   self.dest.resolve(scope, None))

class Setblock(Command):

    def __init__(self, pos, block):
        assert isinstance(pos, WorldPos) and pos.block_pos
        self.pos = pos
        self.block = block

    def resolve(self, scope, fmt=None):
        return 'setblock %s %s' % (self.pos.resolve(scope, None),
                                   self.block.resolve(scope, None))

class TeamModify(Command):

    def __init__(self, team, attr, value):
        assert isinstance(team, TeamName)
        self.team = team
        assert attr in ['color', 'friendlyFire', 'seeFriendlyInvisibles',
                        'nametagVisibility', 'deathMessageVisibility',
                        'collisionRule', 'displayName', 'prefix', 'suffix']
        self.attr = attr
        self.value = value

    def resolve(self, scope, fmt=None):
        return 'team modify %s %s %s' % (self.team.resolve(scope, None), self.attr,
                                         self.value)

class JoinTeam(Command):

    def __init__(self, team, members):
        assert isinstance(team, TeamName)
        assert members is None or isinstance(members, EntityRef)
        self.team = team
        self.members = members

    def resolve(self, scope, fmt=None):
        members = (' ' + self.members.resolve(scope, None)) if self.members else ''
        return 'team join %s%s' % (self.team.resolve(scope, None), members)

class BossbarSet(Command):

    def __init__(self, bar, prop, value):
        assert isinstance(bar, Bossbar)
        self.bar = bar
        self.prop = prop
        self.value = value

    def resolve(self, scope, fmt=None):
        value = (' ' + self.value.resolve(scope, None)) if self.value else ''
        return 'bossbar set %s %s%s' % (self.bar.resolve(scope, None), self.prop,
                                        value)

class Kill(Command):

    def __init__(self, target):
        assert isinstance(target, EntityRef)
        self.target = target

    def resolve(self, scope, fmt=None):
        return 'kill %s' % self.target.resolve(scope, None)

class ReplaceItem(Command):

    def __init__(self, ref, slot, item, amount=None):
        assert isinstance(ref, NBTStorable)
        self.ref = ref
        self.slot = slot
        self.item = item
        self.amount = amount

    def resolve(self, scope, fmt=None):
        amount = (' %d' % self.amount) if self.amount is not None else ''
        return 'replaceitem %s %s %s%s' % (self.ref.resolve(scope, None), self.slot,
                                           self.item.resolve(scope, None), amount)

class GiveItem(Command):

    def __init__(self, targets, item, count=1):
        assert isinstance(targets, EntityRef)
        self.targets = targets
        self.item = item
        self.count = count

    def resolve(self, scope, fmt=None):
        return 'give %s %s %d' % (self.targets.resolve(scope, None),
                                  self.item.resolve(scope, None), self.count)

class ClearItem(Command):

    def __init__(self, targets, item, max_count=-1):
        assert isinstance(targets, EntityRef)
        self.targets = targets
        self.item = item
        self.max_count = max_count

    def resolve(self, scope, fmt=None):
        return 'clear %s %s %d' % (self.targets.resolve(scope, None),
                                   self.item.resolve(scope, None), self.max_count)

class EffectGive(Command):

    def __init__(self, target, effect, seconds=None, amp=None, hide=None):
        assert isinstance(target, EntityRef)
        self.target = target
        self.effect = effect
        self.seconds = seconds if seconds is not None else 30
        self.amp = amp if amp is not None else 0
        self.hide = hide if hide is not None else False

    def resolve(self, scope, fmt=None):
        return 'effect give %s %s %d %d %s' % (self.target.resolve(scope, None),
                                               self.effect, self.seconds, self.amp,
               'true' if self.hide else 'false')

class Particle(Command):

    def __init__(self, name, pos, delta, speed, count, mode, players):
        self.name = name
        self.pos = pos
        self.delta = delta
        self.speed = speed
        self.count = count
        self.mode = mode
        self.players = players

    def resolve(self, scope, fmt=None):
        players = (' ' + self.players.resolve(scope, None)) if self.players else ''
        return 'particle %s %s %s %f %d %s%s' % (self.name,
                                                 self.pos.resolve(scope, None), self.delta.resolve(scope, None),
                                                 self.speed, self.count, self.mode, players)

class Title(Command):

    def __init__(self, target, action, *args):
        assert isinstance(target, EntityRef)
        self.target = target
        self.action = action
        self.args = args

    def resolve(self, scope, fmt=None):
        args = (' ' + SimpleResolve(*self.args).resolve(scope, None)) \
               if self.args else ''
        return 'title %s %s%s' % (self.target.resolve(scope, None), self.action, args)

class Summon(Command):

    def __init__(self, entity_name, pos, data=None):
        assert pos is None or isinstance(pos, WorldPos)
        self.name = entity_name
        self.pos = pos
        self.data = data

    def resolve(self, scope, fmt=None):
        pos = (' ' + self.pos.resolve(scope, None)) if self.pos else \
              (' ~ ~ ~' if self.data else '')
        data = (' ' + self.data.resolve(scope, None)) if self.data else ''
        return 'summon %s%s%s' % (self.name, pos, data)

class Advancement(Command):

    def __init__(self, action, target, range, *args):
        assert action in ['grant', 'revoke']
        assert isinstance(target, EntityRef)
        self.action = action
        self.target = target
        self.range = range
        self.args = args

    def resolve(self, scope, fmt=None):
        args = (' ' + SimpleResolve(*self.args).resolve(scope, None)) \
               if self.args else ''
        return 'advancement %s %s %s%s' % (self.action,
                                           self.target.resolve(scope, None),
                                            self.range, args)
