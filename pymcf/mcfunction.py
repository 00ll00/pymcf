import sys
from types import FunctionType
from typing import Any, Set, List

from pymcf.datas.entity.entity import _Self
from pymcf import logger
from pymcf.datas.datas import InGameData, InGameObj
from pymcf.operations import CallFunctionOp, CallMethodOp
from pymcf.project import Project
from pymcf.codes import CodeTypeRewriter
from pymcf.context import MCFContext
from pymcf.util import staticproperty
import ast

compile()

class mcfunction:
    """
    Make mcfunction from marked function.

    use kwargs when setting parameter.
    """

    def __new__(cls, __func=None, tags: Set[str] = None, is_entry_point: bool = False, inline: bool = False):
        self = super(mcfunction, cls).__new__(cls)
        self.__init__(tags if tags is not None else set(), is_entry_point, inline)

        if __func is not None:
            self._wrap_func(__func)

        def caller(*args, **kwargs):
            # a function decorated by mcfunction will be replaced by `caller`
            # caller function can receive `self` when decorating a class method
            if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], FunctionType):
                # accepted a function object, init factory, return caller
                func = args[0]
                self._wrap_func(func)
                return caller
            else:
                # accepted params, make function invoke (generate mcfunction files)
                # noinspection PyUnresolvedReferences
                return self._generate(args, kwargs, sys._getframe(1))

        setattr(caller, "__str__", property(lambda: self.name))

        return caller

    def __init__(self, tags=None, is_entry_point=None, inline=None):
        # __init__ will not be invoked automatic, use for type hint
        self.proj: Project = Project.INSTANCE
        self.tags: Set[str] = tags
        self.ep: bool = is_entry_point
        self.inline: bool = inline
        self.is_method = False

        assert not (self.ep and self.inline), "entrypoint mcfunction cannot be inline"

        self.name = None
        self.generator = None
        self.g_globals = None

        self.pars: List[MCFParamAndRes] = []

    def __call__(self, *args, **kwargs):
        # make mcfunction callable, for type hint only
        # real invoke handler is caller
        ...

    @staticmethod
    def _is_method(func):
        """
        detect first arg name of the function is "self" or not
        """
        code = func.__code__
        if code.co_argcount > 0 and code.co_varnames[0] == "self":
            return True
        return False

    def _wrap_func(self, func):
        # build mcfunction generator of given func
        self.is_method = self._is_method(func)
        if self.ep and (func.__code__.co_argcount > 0 or func.__code__.co_kwonlyargcount > 0):
            raise RuntimeError(f"Entry point mcfunction cannot have arguments: {func}")
        self.name = func.__qualname__.replace('.', '/').lower()

        try:
            pyc = CodeTypeRewriter(func.__code__)
        except SyntaxError as exc:
            raise SyntaxError(f"unsupported syntax used in mcfunction: {self.name}.", exc)
        glb = func.__globals__.copy()
        glb.update(pyc.globals)
        self.g_globals = glb
        self.generator = FunctionType(pyc.codetype, glb)

        self.proj.add_mcf(self)

    def _get_index(self, args, kwargs) -> int:
        for i, par in enumerate(self.pars):
            if par.is_same_arg_structure(args, kwargs):
                return i
        return len(self.pars)

    def gen_ep(self):
        """
        for project.build() only
        """
        assert self.ep
        # noinspection PyUnresolvedReferences
        self._generate((), {}, sys._getframe(2))  # gen_ep is two frames from caller

    def _generate(self, args, kwargs, frame) -> Any:
        """
        the factory function to generate parametrized mcfunction.
        """
        glb = frame.f_globals.copy()
        glb.update(self.g_globals)
        glb.update(frame.f_locals)
        self.generator.__globals__.clear()
        self.generator.__globals__.update(glb)
        return_value = None
        if self.inline:
            # don't create a new file and don't record anything for inline func
            return_value = self.generator.__call__(*args, **kwargs)
        else:
            idx = self._get_index(args, kwargs)
            if self.ep and idx != 0:
                logger.warning("Enter point mcfunction should not have index.")
            ctx_name = self.name + '.' + str(idx) if not self.ep else self.name

            # check function parameters
            if idx == len(self.pars):
                par = MCFParamAndRes()
                self.pars.append(par)
                par.set_arg(args, kwargs)
                # generate new func
                if not self.ep:
                    args, kwargs = par.make_arg_copy(self.is_method)
                with MCFContext(ctx_name, tags=self.tags, is_enter_point=self.ep):
                    res = self.generator.__call__(*args, **kwargs)
                par.set_return_value(res)
                par.set_globals(self.generator.__globals__)
                par.update_globals(frame)
                if not self.ep:
                    if self.is_method:
                        CallMethodOp(args[0], ctx_name)
                        args[0]._unwrap_()
                    else:
                        CallFunctionOp(ctx_name)
                    return_value = par.make_res_copy()
            else:
                # load old result
                par = self.pars[idx]
                par.update_globals(frame)
                if not self.ep:
                    par.make_copy_to_args(args, kwargs)
                    if self.is_method:
                        CallMethodOp(args[0]._origin_identifier, ctx_name)
                    else:
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
        self.args: tuple | None = None
        self.kwargs: dict | None = None
        self.return_value: None | tuple | InGameData = None
        self.globals: dict | None = None

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

    def make_arg_copy(self, is_method):
        if is_method:
            ca = tuple((_Self(self.args[0]), *(a._new_from_() if isinstance(a, InGameObj) else a for a in self.args[1:])))
        else:
            ca = tuple(a._new_from_() if isinstance(a, InGameObj) else a for a in self.args)
        ckwa = dict((k, v._new_from_() if isinstance(v, InGameObj) else v) for k, v in self.kwargs.items())
        self.args = ca
        self.kwargs = ckwa
        return ca, ckwa

    def make_res_copy(self):
        if self.return_value is None:
            return None
        elif isinstance(self.return_value, tuple):
            return tuple(r._new_from_() for r in self.return_value)
        else:
            return self.return_value._new_from_()

    def make_copy_to_args(self, args, kwargs):
        for i in range(len(self.args)):
            if isinstance(args[i], InGameObj):
                args[i]._transfer_to_(self.args[i])

        for k in kwargs.keys():
            if isinstance(args[k], InGameObj):
                kwargs[k]._transfer_to_(self.kwargs[k])

    def update_globals(self, frame):
        for key in frame.f_locals:
            if key in self.globals:
                frame.f_locals[key] = self.globals[key]

    def is_same_arg_structure(self, args: tuple, kwargs: dict):
        if len(args) != len(self.args) or kwargs.keys() != self.kwargs.keys():
            return False

        for i in range(len(self.args)):
            if type(self.args[i]) is not type(args[i]):
                return False
            if isinstance(args[i], InGameObj) and not self.args[i]._compatible_to_(args[i]):
                return False

        for k in kwargs.keys():
            if type(self.args[k]) is not type(args[k]):
                return False
            if isinstance(args[k], InGameObj) and not self.args[k]._is_same_structure_(args[k]):
                return False

        return True

    @staticmethod
    def _check_return_ingame(data):
        if not isinstance(data, InGameObj):
            logger.error("mcfunction can only return None, InGameObj or tuple of InGameObj.")
            raise TypeError()
