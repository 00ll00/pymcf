import functools
import inspect
from collections import defaultdict
from contextvars import ContextVar
from types import FunctionType, MethodType
from typing import Self, overload, Iterable, Any

from pymcf.ast_ import Constructor, reform_func, Call, Scope, compiler_hint, Resolvable, RtBaseVar, RtBaseExc
from pymcf.ast_.runtime import RtCtxManager
from pymcf.ir.codeblock import IrBlockAttr


class CompileTimeError(BaseException):
    """
    编译期的异常泄露会导致编译的代码流程出现异常，此异常不应被捕获
    """


type _CtArg = (
    bool |
    int | float | complex | str | None |
    list[_CtArg] | tuple[_CtArg, ...] | dict[_CtArg, _CtArg] | set[_CtArg]
)
"""
允许作为参数传入 mcfunction 的编译期量
"""


class FuncArgs:
    def __init__(self, args: dict[str, _CtArg]) -> None:
        self.ct_args = {}
        self.rt_args = {}
        for k, v in args.items():
            if isinstance(v, RtBaseVar):
                self.rt_args[k] = v
            else:
                self.ct_args[k] = v

    def __eq__(self, other: Self) -> bool:
        # TODO
        # with set_eq_identifier(True):
        if self.ct_args != other.ct_args:
            return False
        if len(self.rt_args) != len(other.rt_args):
            return False
        for k, v in self.rt_args.items():
            if k not in other.rt_args:
                return False
            if type(v) != type(other.rt_args[k]):
                return False
        return True

    def __assign__(self, other: Self):
        assert self == other
        for k, v in self.rt_args.items():
            v.__assign__(other.rt_args[k])

    def get_args(self) -> dict[str, Any]:
        return {**self.rt_args, **self.ct_args}

    def __create_var__(self) -> Self:
        args = self.ct_args.copy()
        args.update({k: v.__create_var__() for k, v in self.rt_args.items()})
        return FuncArgs(args)

def get_valid_name(func_name: str) -> str:
    return (func_name
            .replace("$wrapper.<locals>.", "")
            .replace("<", "-")
            .replace(">", "-")
            .replace(".", "/"))


class Executor:
    """
    包装实体，作为第一个参数传入 mcfunction 时表示此方法调用时需要切换执行者
    """
    def __init__(self, entity):
        self.entity = entity

_mcfunction_registry = defaultdict(functools.partial(defaultdict, dict))

# noinspection PyPep8Naming
class mcfunction:
    """
    @mcfunction
    def func(): ...

    entrance: 是否为入口函数（手动调用或由#load/#tick标签调用）
    tags: 函数标签
    inline: 是否内联
    """

    _all: list[Self] = []

    def __new__(cls, _func=None, /, **kwargs):

        def wrap(func):
            if not inspect.isfunction(func):
                raise TypeError(f"{func!r} 不是一个函数。")
            try:
                inspect.getsource(func)
            except OSError:
                raise ValueError(f"无法获取函数 {func.__module__}.{func.__qualname__} 的源代码。")

            self = _mcfunction_registry[func.__module__][func.__qualname__].get(func.__code__.co_firstlineno)
            if self is None:
                self = object.__new__(cls)
                _mcfunction_registry[func.__module__][func.__qualname__][func.__code__.co_firstlineno] = self

            if _func is None:
                # 说明返回的是 wrapper，需要手动 init
                self.__init__(func, **kwargs)
            return self

        if _func is None:
            return wrap
        else:
            return wrap(_func)

    def __init__(self,_func: FunctionType=None, /, * ,  # _func 默认 None 仅用于避免编辑器提示缺少参数
                 tags: set[str] = None,
                 entrance: bool = False,
                 inline: bool = False,
                 func_name: str = None,
                 throws: Iterable[type[RtBaseExc]] = None,
                 **kwargs,
                 ):
        assert _func is not None

        # 避免重复 init
        if "__init_flag" in self.__dict__:
            return
        self.__dict__["__init_flag"] = True

        self.__name__ = _func.__name__
        self.__doc__ = _func.__doc__
        self.__module__ = _func.__module__
        self.__qualname__ = _func.__qualname__

        self._origin_func = _func
        self._signature = inspect.signature(_func)

        self._ast_generator = reform_func(_func, wrapper_name="$wrapper")

        self._arg_scope: list[tuple[FuncArgs, Scope | Constructor]] = []

        self._tags = tags if tags is not None else set()
        self._entrance = entrance
        self._inline = inline

        self._throws = throws  # TODO 指定的异常集和真实异常集的冲突检查

        if func_name is None:
            basename = _func.__qualname__.lower()
            if _func.__module__ != "__main__":
                basename = _func.__module__.lower() + '.' + basename
        else:
            basename = func_name

        self._basename = get_valid_name(basename)
        if self._inline:
            self.name = self._basename + "@inlined"
        else:
            self.name = self._basename

        mcfunction._all.append(self)

    def __call__(self, *args, **kwargs):
        from .mc.scope import MCFScope
        executor = None
        if len(args) > 0 and isinstance(args[0], Executor):
            if not self._inline:
                # TODO
                executor = args[0].entity
            args = (args[0].entity, *args[1:])
        bound_arg = self._signature.bind(*args, **kwargs)  # TODO nonlocal 是否应当作为参数进行记录
        bound_arg.apply_defaults()
        if self._inline:
            with Constructor(name=self._basename, inline=self._inline, scope=Constructor.current_constr().scope) as constr:
                self._ast_generator(*bound_arg.args, **bound_arg.kwargs)
            constr.finish()
            return constr.return_value
        else:
            last_constr = Constructor.current_constr()

            func_arg = FuncArgs(bound_arg.arguments)
            for func_param, scope_or_constr in self._arg_scope:
                if func_param == func_arg:
                    if last_constr is not None:
                        func_param.__assign__(func_arg)
                        scope = scope_or_constr if isinstance(scope_or_constr, Scope) else scope_or_constr.scope
                        last_constr.record_statement(Call(scope, _offline=True))
                    else:
                        assert self._entrance
                    return scope_or_constr.return_value

            if self._entrance and len(self._arg_scope) == 0:
                ext = ""
            else:
                ext = "-" + str(len(self._arg_scope))

            func_name = f"{self._basename}{ext}"
            with Constructor(name=func_name, inline=self._inline, scope=MCFScope(name=func_name, executor=executor, tags=self._tags, set_throws=self._throws)) as constr:
                func_param = func_arg.__create_var__()
                self._arg_scope.append((func_param, constr))
                bound_arg_ = self._signature.bind(**func_param.get_args())
                self._ast_generator(*bound_arg_.args, **bound_arg_.kwargs)
            constr.finish()

            if last_constr is not None:
                func_param.__assign__(func_arg)
                last_constr.record_statement(Call(constr.scope, _offline=True))
            else:
                assert self._entrance

            for i, (args, _) in enumerate(self._arg_scope):
                if args is func_arg:
                    break
            self._arg_scope[i] = (func_arg, constr.scope)

            return constr.return_value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        from pymcf.data import Entity
        if issubclass(owner, Entity):
            return MethodType(self, Executor(instance))
        else:
            return MethodType(self, instance)

    @staticmethod
    def inline(_func=None, /, **kwargs):
        return mcfunction(_func, inline=True, tags=None, entrance=False, **kwargs)

    @staticmethod
    def manual(_func=None, /, *, tags: set[str] = None, **kwargs):
        return mcfunction(_func, inline=False, tags=tags, entrance=True, **kwargs)

    @staticmethod
    def load(_func=None, /, *, tags: set[str] = None, **kwargs):
        if tags is None:
            tags = {}
        return mcfunction(_func, inline=False, tags={*tags, "load"}, entrance=True, **kwargs)

    @staticmethod
    def tick(_func=None, /, *, tags: set[str] = None, **kwargs):
        if tags is None:
            tags = {}
        return mcfunction(_func, inline=False, tags={*tags, "tick"}, entrance=True, **kwargs)


class execute(RtCtxManager):
    def __init__(self, *conv: str | Resolvable):
        self.conv = conv
    def __enter__(self):
        IrBlockAttr({"execute": self.conv})
    def __exit__(self, exc_type, exc_value, traceback):
        pass  # TODO 异常处理内联后可能让函数处于不正确的上下文
    def __repr__(self):
        return f"execute({self.conv!r})"