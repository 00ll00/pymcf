import os.path
from typing import Type


class staticproperty:

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func()


class lazy:

    def __init__(self, func):
        self.func = func
        self.loaded = False
        self.value = None

    def __call__(self, *args, **kwargs):
        if not self.loaded:
            self.loaded = True
            self.value = self.func(*args, **kwargs)
        return self.value


def staticclass(cls: Type):
    """
    class decorator, make a class static.
    the class will be replaced by the singleton instance.

    static class should have no init parameter, use type(cls) get origin class of static class.
    """
    instance = cls()
    cls.__new__ = lambda *_, **__: instance
    cls.__init__ = lambda *_, **__: None
    return instance


Null = object()
"""
second None
"""


def create_file_dir(filepath: str):
    filedir = filepath.replace('\\', '/').rsplit('/', 1)[0]
    if not os.path.exists(filedir):
        os.makedirs(filedir)
