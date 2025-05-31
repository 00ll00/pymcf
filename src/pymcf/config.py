import abc
from collections import defaultdict
from typing import Self


class _TypeRec:
    def __init__(self):
        self.typ = NotImplemented
        self.default = None
        self.def_cls = []

    def add_def(self, typ: type, cls: type, default=None) -> bool:
        if self.typ is not NotImplemented and self.typ != typ:
            return False
        self.typ = typ  # TODO 考虑特殊类型兼容
        if default is not None and self.default is not None and self.default != default:
            return False
        if default is not None:
            self.default = default
        self.def_cls.append(cls)
        return True


_items: dict[str, _TypeRec]= defaultdict(lambda: _TypeRec())
_queried_keys = set()


class Config:

    def __init__(self, _parent: Self=None, **kwargs):
        self._parent = _parent
        self._cfg = {**kwargs}

    def __getattr__(self, item):
        if item.startswith('_'):
            raise AttributeError
        _queried_keys.add(item)
        return self._cfg.get(item, self._parent.__getattr__(item) if self._parent else _items[item].default)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super().__setattr__(key, value)
        else:
            self._cfg[key] = value

    def __init_subclass__(cls, **kwargs):
        for key, typ in cls.__annotations__.items():
            if key.startswith('_'):
                raise KeyError(f"配置项不能以'_'开头：{cls.__qualname__}.{key}")
            if not _items[key].add_def(typ, cls, getattr(cls, key, None)):
                raise TypeError(
                    f"{cls.__qualname__}.{key} 的定义与 {', '.join(c.__qualname__ for c in _items[key].def_cls)} 存在冲突")

        def no_instance(cls, *_, **__):
            raise TypeError(f"{cls.__qualname__} cannot be instantiated")

        cls.__new__ = no_instance

        return cls

    def push(self, cfg: Self): ...
    def pop(self): ...
    # TODO


def dump_config(config: Config = None) -> str:
    if config is None:
        config = Config()
    res = ""
    for key in _items:
        res += f"{'+' if key in _queried_keys else ' '} {key}: {_items[key].typ} = {getattr(config, key)}\n"
    return res