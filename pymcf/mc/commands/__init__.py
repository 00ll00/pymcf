from .core import *
from .execute import *
from .nbt import *
from .scoreboard import *
from .selector import *
from .text import *

class Cmd(Command):
    def __init__(self, cmd):
        self.command = cmd

    def resolve(self, ctx):
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
                replace = ctx.function_name(NSName('sub_' + m.group(2)))
            else:
                replace = ctx.objective(m.group(2))
            cmd = cmd[:m.start()] + replace + cmd[m.end():]
        return cmd

class Function(Command):

    def __init__(self, func_name):
        assert isinstance(func_name, NSName)
        self.name = func_name

    def resolve(self, ctx):
        return 'function %s' % ctx.function_name(self.name)

class FunctionTag(Command):

    def __init__(self, tag_name):
        assert isinstance(tag_name, NSName)
        self._name = tag_name

    def resolve(self, ctx):
        return 'function #' + ctx.func_tag_name(self._name)

class Teleport(Command):

    def __init__(self, target, *more):
        assert isinstance(target, EntityRef)
        self.args = [target]
        self.args.extend(more)

    def resolve(self, ctx):
        return 'tp %s' % ' '.join(a.resolve(ctx) for a in self.args)

class Clone(Command):

    def __init__(self, src0, src1, dest):
        self.src0 = src0
        self.src1 = src1
        self.dest = dest

    def resolve(self, ctx):
        return 'clone %s %s %s' % (self.src0.resolve(ctx),
                                   self.src1.resolve(ctx),
                                   self.dest.resolve(ctx))

class Setblock(Command):

    def __init__(self, pos, block):
        assert isinstance(pos, WorldPos) and pos.block_pos
        self.pos = pos
        self.block = block

    def resolve(self, ctx):
        return 'setblock %s %s' % (self.pos.resolve(ctx),
                                   self.block.resolve(ctx))

class TeamModify(Command):

    def __init__(self, team, attr, value):
        assert isinstance(team, TeamName)
        self.team = team
        assert attr in ['color', 'friendlyFire', 'seeFriendlyInvisibles',
                        'nametagVisibility', 'deathMessageVisibility',
                        'collisionRule', 'displayName', 'prefix', 'suffix']
        self.attr = attr
        self.value = value

    def resolve(self, ctx):
        return 'team modify %s %s %s' % (self.team.resolve(ctx), self.attr,
                                         self.value)

class JoinTeam(Command):

    def __init__(self, team, members):
        assert isinstance(team, TeamName)
        assert members is None or isinstance(members, EntityRef)
        self.team = team
        self.members = members

    def resolve(self, ctx):
        members = (' ' + self.members.resolve(ctx)) if self.members else ''
        return 'team join %s%s' % (self.team.resolve(ctx), members)

class BossbarSet(Command):

    def __init__(self, bar, prop, value):
        assert isinstance(bar, Bossbar)
        self.bar = bar
        self.prop = prop
        self.value = value

    def resolve(self, ctx):
        value = (' ' + self.value.resolve(ctx)) if self.value else ''
        return 'bossbar set %s %s%s' % (self.bar.resolve(ctx), self.prop,
                                        value)

class Kill(Command):

    def __init__(self, target):
        assert isinstance(target, EntityRef)
        self.target = target

    def resolve(self, ctx):
        return 'kill %s' % self.target.resolve(ctx)

class ReplaceItem(Command):

    def __init__(self, ref, slot, item, amount=None):
        assert isinstance(ref, NBTStorable)
        self.ref = ref
        self.slot = slot
        self.item = item
        self.amount = amount

    def resolve(self, ctx):
        amount = (' %d' % self.amount) if self.amount is not None else ''
        return 'replaceitem %s %s %s%s' % (self.ref.resolve(ctx), self.slot,
                                           self.item.resolve(ctx), amount)

class GiveItem(Command):

    def __init__(self, targets, item, count=1):
        assert isinstance(targets, EntityRef)
        self.targets = targets
        self.item = item
        self.count = count

    def resolve(self, ctx):
        return 'give %s %s %d' % (self.targets.resolve(ctx),
                                  self.item.resolve(ctx), self.count)

class ClearItem(Command):

    def __init__(self, targets, item, max_count=-1):
        assert isinstance(targets, EntityRef)
        self.targets = targets
        self.item = item
        self.max_count = max_count

    def resolve(self, ctx):
        return 'clear %s %s %d' % (self.targets.resolve(ctx),
                                   self.item.resolve(ctx), self.max_count)

class EffectGive(Command):

    def __init__(self, target, effect, seconds=None, amp=None, hide=None):
        assert isinstance(target, EntityRef)
        self.target = target
        self.effect = effect
        self.seconds = seconds if seconds is not None else 30
        self.amp = amp if amp is not None else 0
        self.hide = hide if hide is not None else False

    def resolve(self, ctx):
        return 'effect give %s %s %d %d %s' % (self.target.resolve(ctx),
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

    def resolve(self, ctx):
        players = (' ' + self.players.resolve(ctx)) if self.players else ''
        return 'particle %s %s %s %f %d %s%s' % (self.name,
                                                 self.pos.resolve(ctx), self.delta.resolve(ctx),
                                                 self.speed, self.count, self.mode, players)

class Title(Command):

    def __init__(self, target, action, *args):
        assert isinstance(target, EntityRef)
        self.target = target
        self.action = action
        self.args = args

    def resolve(self, ctx):
        args = (' ' + SimpleResolve(*self.args).resolve(ctx)) \
               if self.args else ''
        return 'title %s %s%s' % (self.target.resolve(ctx), self.action, args)

class Summon(Command):

    def __init__(self, entity_name, pos, data=None):
        assert pos is None or isinstance(pos, WorldPos)
        self.name = entity_name
        self.pos = pos
        self.data = data

    def resolve(self, ctx):
        pos = (' ' + self.pos.resolve(ctx)) if self.pos else \
              (' ~ ~ ~' if self.data else '')
        data = (' ' + self.data.resolve(ctx)) if self.data else ''
        return 'summon %s%s%s' % (self.name, pos, data)

class Advancement(Command):

    def __init__(self, action, target, range, *args):
        assert action in ['grant', 'revoke']
        assert isinstance(target, EntityRef)
        self.action = action
        self.target = target
        self.range = range
        self.args = args

    def resolve(self, ctx):
        args = (' ' + SimpleResolve(*self.args).resolve(ctx)) \
               if self.args else ''
        return 'advancement %s %s %s%s' % (self.action,
                                            self.target.resolve(ctx),
                                            self.range, args)
