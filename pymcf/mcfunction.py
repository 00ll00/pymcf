import inspect
from contextvars import ContextVar
from types import FunctionType, MethodType
from typing import Self

from pymcf.ast_ import Constructor, reform_func, Call, Scope


class CompileTimeError(BaseException):
    """
    编译期的异常泄露会导致编译的代码流程出现异常，此异常不应被捕获
    """


_generating: ContextVar[bool] = ContextVar('_generating', default=False)
"""
是否已经在生成过程中
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
        self.args = args

    def __eq__(self, other: Self) -> bool:
        # TODO
        # with set_eq_identifier(True):
        return self.args == other.args
        # return False

    def __hash__(self) -> int:
        # TODO
        h = 0
        for k, v in self.args.items():
            h ^= hash(k)
            try:
                h ^= hash(v)
            except TypeError:
                ...
        return h


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
            if _generating.get():
                return func  # 如果是在构建中，直接返回原函数避免套娃
            if not inspect.isfunction(func):
                raise TypeError(f"{func!r} 不是一个函数。")
            try:
                inspect.getsource(func)
            except OSError:
                raise ValueError(f"无法获取函数 {func.__module__}.{func.__qualname__} 的源代码。")
            self = object.__new__(cls)
            if _func is None:
                # 说明返回的是 wrapper，需要手动 init
                self.__init__(func, **kwargs)
            return self

        if _func is None:
            return wrap
        else:
            return wrap(_func)

    def __init__(self,_func: FunctionType, /, * ,
                 tags: set[str] = None,
                 entrance: bool = False,
                 inline: bool = False,
                 func_name: str = None,
                 **kwargs,
                 ):
        self.__name__ = _func.__name__
        self.__doc__ = _func.__doc__
        self.__module__ = _func.__module__
        self.__qualname__ = _func.__qualname__

        self._origin_func = _func
        self._signature = inspect.signature(_func)
        _generating.set(True)
        try:
            self._ast_generator = reform_func(_func, wrapper_name="$wrapper")
        finally:
            _generating.set(False)

        self._arg_scope: dict[FuncArgs, Scope] = {}

        self._tags = tags if tags is not None else set()
        self._entrance = entrance
        self._inline = inline

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
        if self._inline:
            with Constructor(name=self._basename, inline=self._inline, scope=Constructor.current_constr().scope) as constr:
                self._ast_generator(*args, **kwargs)
            constr.finish()
            return constr.return_value
        else:
            func_arg = FuncArgs(self._signature.bind(*args, **kwargs).arguments)
            if func_arg in self._arg_scope:
                return self._arg_scope[func_arg].return_value

            if self._entrance and len(self._arg_scope) == 0:
                ext = ""
            else:
                ext = "-" + str(len(self._arg_scope))

            last_constr = Constructor.current_constr()
            func_name = f"{self._basename}{ext}"
            with Constructor(name=func_name, inline=self._inline, scope=MCFScope(name=func_name, executor=executor, tags=self._tags)) as constr:
                self._ast_generator(*args, **kwargs)
            constr.finish()

            if not self._entrance and not self._inline:
                assert last_constr is not None
                last_constr.record_statement(Call(constr.scope, _offline=True))

            self._arg_scope[func_arg] = constr.scope

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