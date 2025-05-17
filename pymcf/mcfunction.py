import inspect
from contextvars import ContextVar
from types import FunctionType, MethodType

from pydantic import BaseModel

from pymcf.ast_ import Context, reform_func, Call


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


class Args(BaseModel):
    args: tuple[_CtArg, ...]


# noinspection PyPep8Naming
class mcfunction:
    """
    @mcfunction
    def func(): ...

    entrance: 是否为入口函数（手动调用或由#load/#tick标签调用）
    tags: 函数标签
    inline: 是否内联
    """

    def __new__(cls, _func=None, /, **kwargs):

        def wrap(func):
            if _generating.get():
                return func  # 如果是在构建中，直接返回原函数避免套娃
            if not inspect.isfunction(func):
                raise TypeError(f"{func!r} 不是一个函数。")
            try:
                inspect.getsource(func)
            except OSError:
                raise ValueError(f"无法获取函数 {func.__qualname__} 的源代码。")
            self = object.__new__(cls)
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
                 ):
        self.__name__ = _func.__name__
        self.__doc__ = _func.__doc__
        self.__module__ = _func.__module__
        self.__qualname__ = _func.__qualname__

        self._origin_func = _func
        self._signature = inspect.signature(_func)

        _generating.set(True)
        try:
            self._ast_generator = reform_func(_func)
        finally:
            _generating.set(False)

        self._ctx_list: list[Context] = []

        self._tags = tags if tags is not None else set()
        self._entrance = entrance
        self._inline = inline
        self._basename = _func.__qualname__

    def __call__(self, *args, **kwargs):
        #TODO mcf 调用参数检查
        last_ctx = Context.current_ctx()
        with Context(self._basename, inline=self._inline) as ctx:
            self._ast_generator(*args, **kwargs)
        ctx.finish()

        if not self._entrance and not self._inline:
            assert last_ctx is not None
            last_ctx.record_statement(Call(ctx, _offline=True))

        self._ctx_list.append(ctx)

        return ctx._return_value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return MethodType(self, instance)

    @staticmethod
    def inline(_func=None, /):
        def wrap(func):
            return mcfunction(func, inline=True, tags=None, entrance=False)
        if _func is None:
            return wrap
        else:
            return wrap(_func)

    @staticmethod
    def manual(_func=None, /, *, tags: set[str] = None):
        def wrap(func):
            return mcfunction(func, inline=False, tags=tags, entrance=True)
        if _func is None:
            return wrap
        else:
            return wrap(_func)

    @staticmethod
    def load(_func=None, /):
        def wrap(func):
            return mcfunction(func, inline=False, tags={"load"}, entrance=True)
        if _func is None:
            return wrap
        else:
            return wrap(_func)

    @staticmethod
    def tick(_func=None, /):
        def wrap(func):
            return mcfunction(func, inline=False, tags={"tick"}, entrance=True)
        if _func is None:
            return wrap
        else:
            return wrap(_func)