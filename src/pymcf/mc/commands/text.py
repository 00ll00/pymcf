import json
from abc import abstractmethod

from pymcf.mc.commands import Selector

from .core import Command, EntityRef, Resolvable
from .scoreboard import ScoreRef
from .nbt import Path, NBTStorable

class Tellraw(Command):

    def __init__(self, text, target):
        assert isinstance(text, TextComponentHolder)
        assert isinstance(target, EntityRef)
        self.text = text
        self.target = target

    def resolve(self, scope):
        return 'tellraw %s %s' % (self.target.resolve(scope),
                                  self.text.resolve(scope))

class TextComponent(Resolvable):
    def resolve(self, scope):
        return json.dumps(self._resolve(scope), separators=(',', ':'))

    @abstractmethod
    def _resolve(self, scope): ...

class TextComponentHolder(TextComponent):

    def __init__(self, style, children):
        self.style = style
        self.children = children

    def _resolve(self, scope):
        text = {}
        for key, value in self.style.items():
            text[key] = self._resolve_style(key, value, scope)
        extra = []
        for child in self.children:
            if isinstance(child, TextComponentHolder) and not child.style:
                for child_child in child.children:
                    extra.append(child_child._resolve(scope))
            else:
                extra.append(child._resolve(scope))
        if not self.style:
            return extra
        if extra:
            if len(extra) == 1 and type(extra[0]) == dict:
                text.update(extra[0])
            else:
                text['extra'] = extra
                text['text'] = ""
        return text

    def _resolve_style(self, key, value, scope):
        if key == 'clickEvent':
            assert isinstance(value, TextClickAction)
            return value._resolve(scope)
        return value

class TextStringComponent(TextComponent):

    def __init__(self, stringval):
        self.val = stringval

    def _resolve(self, scope):
        return {'text': self.val}

class TextNBTComponent(TextComponent):

    def __init__(self, storage, path):
        assert isinstance(storage, NBTStorable)
        assert isinstance(path, Path)
        self.storage = storage
        self.path = path

    def _resolve(self, scope):
        obj = {'nbt': self.path.resolve(scope)}
        obj.update(self.storage.as_text(scope))
        return obj

class TextScoreComponent(TextComponent):

    def __init__(self, ref):
        assert isinstance(ref, ScoreRef)
        self.ref = ref

    def _resolve(self, scope):
        return {'score':
                {'name': self.ref.target.resolve(scope),
                 'objective': self.ref.objective.resolve(scope)}}

class TextSelectorCompoment(TextComponent):
    def __init__(self, selector):
        assert isinstance(selector, Selector)
        self.selector = selector
    def _resolve(self, scope):
        return {'selector': self.selector.resolve(scope)}

class TextClickAction:

    def __init__(self, action, value):
        self.action = action
        self.value = value

    def _resolve(self, scope):
        if type(self.value) == str:
            value = self.value
        else:
            assert self.action in ['run_command', 'suggest_command'] \
                   and isinstance(self.value, Command)
            value = self.value.resolve(scope)
        return {'action': self.action, 'value': value}
