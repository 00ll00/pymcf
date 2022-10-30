import sys
from types import FunctionType
from typing import Any, Set, List

from pymcf import logger
from pymcf.datas.datas import InGameData
from pymcf.operations import CallFunctionOp
from pymcf.project import Project
from pymcf.codes import CodeTypeRewriter
from pymcf.context import MCFContext
from pymcf.util import staticproperty


class mcfunction:
    """
    Make mcfunction from marked function
    """

    def __new__(cls, func=None, **kwargs):
        self = super(mcfunction, cls).__new__(cls)
        self.__init__(func, **kwargs)

        def caller(*args1, **kwargs1):
            """
            caller function can receive `self` while decorating a class method.
            """
            self.from_frame = sys._getframe(1)
            self.__call__(*args1, **kwargs1)

        return caller

    def __init__(self, func=None, **kwargs):
        # if func is not None, mean this decorator is used like:
        # @mcfunction
        # def a(): ...
        # in this case, we need to make decorator self behave as a factory
        self.proj: Project = Project.INSTANCE
        self.tags: Set[str] = kwargs["tags"] if "tags" in kwargs else set()
        self.ep: bool = kwargs["is_entry_point"] if "is_entry_point" in kwargs else False
        self.inline: bool = kwargs["inline"] if "inline" in kwargs else False

        assert not (self.ep and self.inline)

        self.name = None
        self.generator = None
        self.factory = None
        self.from_frame = None

        self.pars: List[MCFParamAndRes] = []

        if func is not None:
            self.factory = self.__call__(func)

    def __call__(self, *args, **kwargs):
        """
        if input is a function, build a generator and return the factory function;
        else invoke generator factory with given args.
        """
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], FunctionType) and self.factory is None:
            func = args[0]
            if self.ep and (func.__code__.co_argcount > 0 or func.__code__.co_kwonlyargcount > 0):
                raise RuntimeError(f"Entry point mcfunction cannot have arguments: {func}")
            self.name = func.__qualname__.replace('.', '/').lower()
            self.make_generator(func)
            self.proj.add_mcf(self)
            return self.generate
        else:
            return self.factory(*args, **kwargs)

    def make_generator(self, func):
        pyc = CodeTypeRewriter(func.__code__)
        glb = func.__globals__.copy()
        glb.update(pyc.globals)
        self.generator = FunctionType(pyc.codetype, glb)

    def get_index(self, *args, **kwargs) -> int:
        for i, par in enumerate(self.pars):
            if par.is_same_arg_type(args, kwargs):
                return i
        return len(self.pars)

    def generate(self, *args, **kwargs) -> Any:
        """
        the factory function to generate parametrized mcfunction.
        """
        self.generator.__globals__.update(self.from_frame.f_locals)
        return_value = None
        if self.inline:
            # don't creat a new file and don't record anything for inline func
            return_value = self.generator(*args, **kwargs)
        else:
            idx = self.get_index(*args, **kwargs)
            if self.ep and idx != 0:
                logger.warning("Enter point mcfunction should not have index.")
            ctx_name = self.name + '.' + idx if idx != 0 else self.name

            # check function parameters
            if idx == len(self.pars):
                par = MCFParamAndRes()
                self.pars.append(par)
                par.set_arg(args, kwargs)
                # generate new func
                if not self.ep:
                    args, kwargs = par.make_arg_copy()
                with MCFContext(ctx_name, tags=self.tags, is_enter_point=self.ep) as ctx:
                    res = self.generator(*args, **kwargs)
                par.set_return_value(res)
                par.set_globals(self.generator.__globals__)
                par.update_globals(self.from_frame)
                if not self.ep:
                    CallFunctionOp(ctx_name)
                    return_value = par.make_res_copy()
            else:
                # load old result
                par = self.pars[idx]
                par.update_globals(self.from_frame)
                if not self.ep:
                    par.make_copy_to_args(args, kwargs)
                    CallFunctionOp(ctx_name)
                    return_value = par.make_res_copy()

        return return_value

    # noinspection PyMethodParameters
    @staticproperty
    def load():
        """
        add this mcfunction to tags file minecraft:load
        """
        return mcfunction(tags={"minecraft:load"}, is_entry_point=True)

    # noinspection PyMethodParameters
    @staticproperty
    def tick():
        """
        add this mcfunction to tags file minecraft:tick
        """
        return mcfunction(tags={"minecraft:tick"}, is_entry_point=True)

    # noinspection PyMethodParameters
    @staticproperty
    def manual():
        """
        make this mcfunction a manually triggered entry point
        """
        return mcfunction(is_entry_point=True)

    # noinspection PyMethodParameters
    @staticproperty
    def inline():
        """
        make this mcfunction an inline function
        """
        return mcfunction(is_entry_point=False, inline=True)


class MCFParamAndRes:

    def __init__(self):
        self.args: tuple = None
        self.kwargs: dict = None
        self.return_value: None | tuple | InGameData = None
        self.globals: dict = None

    def set_arg(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def set_return_value(self, res):
        if res is None:
            pass
        elif isinstance(res, tuple):
            for r in res:
                self._check_return_ingame(r)
        else:
            self._check_return_ingame(res)
        self.return_value = res

    def set_globals(self, glb):
        self.globals = glb

    def make_arg_copy(self):
        ca = tuple(a.copy() if isinstance(a, InGameData) else a for a in self.args)
        ckwa = dict((k, v.copy() if isinstance(v, InGameData) else v) for k, v in self.kwargs.items())
        self.args = ca
        self.kwargs = ckwa
        return ca, ckwa

    def make_res_copy(self):
        if self.return_value is None:
            return None
        elif isinstance(self.return_value, tuple):
            return tuple(r.copy() for r in self.return_value)
        else:
            return self.return_value.copy()

    def make_copy_to_args(self, args, kwargs):
        for i in range(len(self.args)):
            if isinstance(args[i], InGameData):
                args[i].copy_to(self.args[i])

        for k in kwargs.keys():
            if isinstance(args[k], InGameData):
                kwargs[k].copy_to(self.kwargs[k])

    def update_globals(self, frame):
        for key in frame.f_locals:
            if key in self.globals:
                frame.f_locals[key] = self.globals[key]

    def is_same_arg_type(self, args: tuple, kwargs: dict):
        if len(args) != len(self.args) or kwargs.keys() != self.kwargs.keys():
            return False

        for i in range(len(self.args)):
            if type(self.args[i]) is not type(args[i]):
                return False
            if isinstance(args[i], InGameData) and not self.args[i].is_same_type(args[i]):
                return False

        for k in kwargs.keys():
            if type(self.args[k]) is not type(args[k]):
                return False
            if isinstance(args[k], InGameData) and not self.args[k].is_same_type(args[i]):
                return False

        return True

    @staticmethod
    def _check_return_ingame(data):
        if isinstance(data, InGameData):
            logger.error("mcfunction can only return None, InGameData or tuple of InGameData.")
            raise TypeError()
