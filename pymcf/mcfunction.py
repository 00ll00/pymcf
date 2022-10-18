from types import FunctionType
from typing import Any, Set

from pymcf import logger
from pymcf.operations import CallFunctionOp
from pymcf.project import Project
from pymcf.codes import PyCode
from pymcf.context import MCFContext
from pymcf.util import staticproperty


class mcfunction:
    """
    Make mcfunction from marked function
    """

    _load = None
    _tick = None

    def __init__(self, func=None, **kwargs):
        # if func is not None, mean this decorator is used like:
        # @mcfunction
        # def a(): ...
        # in this case, we need to make decorator self behave as a factory
        self.proj: Project = Project.INSTANCE
        self.tags: Set[str] = kwargs["tags"] if "tags" in kwargs else set()
        self.ep: bool = kwargs["is_entry_point"] if "is_entry_point" in kwargs else False

        self.name = None
        self.generator = None
        self.as_factory = None

        if func is not None:
            self.as_factory = self.__call__(func)

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], FunctionType) and self.as_factory is None:
            func = args[0]
            if self.ep and (func.__code__.co_argcount > 0 or func.__code__.co_kwonlyargcount > 0):
                raise RuntimeError(f"Entry point mcfunction cannot have arguments: {func}")
            self.name = func.__qualname__
            self.make_generator(func)
            return self.generate
        else:
            self.as_factory(*args, **kwargs)

    def make_generator(self, func):
        pyc = PyCode(func.__code__)
        glb = func.__globals__.copy()
        glb.update(pyc.globals)
        self.generator = FunctionType(pyc.codetype, glb)

    def get_index(self, *args, **kwargs) -> int:
        pass

    def generate(self, *args, **kwargs) -> Any:
        idx = self.get_index(*args, **kwargs)
        if self.ep and idx is not None:
            logger.warning("Enter point mcfunction should not have index.")
        ctx_name = self.name + '.' + idx if idx is not None else self.name
        with MCFContext(ctx_name):
            logger.info(f"generating mcfunction group: {ctx_name}")
            MCFContext.new_file()
            res = self.generator(*args, **kwargs)  # call mcfunction generator
            MCFContext.finish_file()
        if not self.ep:
            CallFunctionOp(ctx_name)
        return res

    # noinspection PyMethodParameters
    @staticproperty
    def load():
        if mcfunction._load is None:
            mcfunction._load = mcfunction(tags={"load"}, is_entry_point=True)
        return mcfunction._load

    # noinspection PyMethodParameters
    @staticproperty
    def tick():
        if mcfunction._tick is None:
            mcfunction._tick = mcfunction(tags={"tick"}, is_entry_point=True)
        return mcfunction._tick
