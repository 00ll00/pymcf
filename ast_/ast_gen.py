import ast
import sys
from ast import *
import inspect
from contextvars import ContextVar
from types import FunctionType
from typing import Any

from . import  Context, ExcSet, Scope
from ._syntactic import ExcHandle, RtUnreachable
from . import syntactic
from .runtime import *


def is_rt_iterator(value) -> bool:
    return isinstance(value, RtBaseIterator)

def is_rt_exception(value) -> bool:
    if isinstance(value, type):
        return issubclass(value, RtBaseExc)
    else:
        return isinstance(value, RtBaseExc)

def enter_scope(scope=None):
    return Context.current_ctx().enter_scope(scope)

def get_pos(node) -> dict:
    if isinstance(node, list):
        if len(node) == 0:
            return {}
        node = node[0]
    res = {}
    for attr in ['lineno', 'col_offset', 'end_lineno', 'end_col_offset']:
        if hasattr(node, attr):
            res[attr] = getattr(node, attr)
    return res

class LiteralExprChecker(NodeVisitor):
    Literals = (
        BoolOp,
        BinOp,
        UnaryOp,
        Lambda,
        IfExp,
        Dict,
        Set,
        ListComp,
        SetComp,
        DictComp,
        GeneratorExp,
        Compare,
        FormattedValue,
        JoinedStr,
        Constant,
        Starred,
        List,
        Tuple,
        Slice,

        expr_context,
        boolop,
        operator,
        unaryop,
        cmpop,
        comprehension,
    )

    def __init__(self):
        self._is_literal = False

    def check(self, node: expr) -> bool:
        """
        检查表达式是否完全由字面量构成
        :param node: 表达式节点
        :return: 是否是字面量
        """
        self._is_literal = True
        self.visit(node)
        return self._is_literal

    def visit(self, node):
        if self._is_literal:
            super().visit(node)

    def generic_visit(self, node):
        if isinstance(node, self.Literals):
            super().generic_visit(node)
        else:
            self._is_literal = False


class ASTRewriter(NodeTransformer):
    """
    python 3.13
    """
    def __init__(self, wrapper_name: str):
        assert sys.version_info.major == 3 and sys.version_info.minor == 13
        self._wrapper_name = wrapper_name
        self._name_id = 0
        self._values = {}
        self._literal_expr_checker = LiteralExprChecker()

    def add_call(self, func, args: list[expr]) -> expr:
        return Call(
            func=self.add_value(func),
            args=args
        )

    def new_name(self) -> str:
        self._name_id += 1
        return f"$var_{self._name_id}"

    def add_value(self, value) -> expr:
        for k, v in self._values.items():
            if v is value:
                name = k
                break
        else:
            name = self.new_name()
            self._values[name] = value
        return Name(
            id=name,
            ctx=Load(),
        )

    def get_glb(self):
        return {k  + '_glb': v for k, v in self._values.items()}

    class ControlFlowHandler:

        def __init__(self):
            self._last_exc: Exception | None = None
            self._iter = iter(self.control_flow())

        def __iter__(self):
            return self._iter

        @abstractmethod
        def control_flow(self):
            ...

        class ExcHandler:
            def __init__(self, handler):
                self._handler = handler
            def __enter__(self):
                ...
            def __exit__(self, exc_type, exc_val, exc_tb):
                self._handler._last_exc = exc_val
                return True

        def exc_handler(self):
            return self.ExcHandler(self)

    def rewrite[F: FunctionDef | AsyncFunctionDef] (self, func_def: F)-> AST:
        node: F = self.generic_visit(func_def)

        name_exc = self.new_name()
        node.body = [
            Try(
                body=node.body,
                handlers=[
                    ExceptHandler(
                        type=self.add_value(RtBaseExc),
                        name=name_exc,
                        body=[
                            Expr(
                                Call(
                                    func=Attribute(value=Name(id=name_exc, ctx=Load()),attr="__record__", ctx=Load()),
                                    args=[],))],)])]

        # 标记 helper value 为 nonlocal
        if  len(self._values) > 0:
            node.body = [
                Nonlocal(names=list(self._values.keys())),
                *node.body,
            ]

        # 外层包裹一层 function def 创建内部闭包环境
        wrapper = FunctionDef(
            name=self._wrapper_name,
            args=arguments(),
            body=[
                node,
                Return(
                    value=Name(id=func_def.name, ctx=Load())
                ),
            ]
        )

        for k, v in self._values.items():
            wrapper.body.insert(
                0,
                Assign(
                    targets=[Name(id=k, ctx=Store())],
                    value=Name(id=k + '_glb', ctx=Load()),
                )
            )

        return Module(
            body=[
                wrapper
            ]
        )

    def generic_visit[T](self, node: T) -> T:
        return super().generic_visit(node)

    def visit(self, node):
        new_node = super().visit(node)

        if new_node is not None and new_node is not node:
            for attr in ['lineno', 'col_offset', 'end_lineno', 'end_col_offset']:
                if attr in new_node._attributes and not hasattr(new_node, attr) and hasattr(node, attr):
                    setattr(new_node, attr, getattr(node, attr))

        return new_node

    class IfHandler(ControlFlowHandler):
        CF_IF = 0
        CF_ELSE = 1
        CF_RAISE = 2

        def __init__(self, condition: Any):
            super().__init__()
            self.condition = condition

        def control_flow(self):
            if isinstance(self.condition, RtBaseData):
                with enter_scope() as sc_body:
                    yield self.CF_IF, None
                    if self._last_exc is not None:
                        if isinstance(self._last_exc, RtBaseExc):
                            self._last_exc.__record__()
                        else:
                            yield self.CF_RAISE, self._last_exc
                with enter_scope() as sc_else:
                    yield self.CF_ELSE, None
                    if self._last_exc is not None:
                        if isinstance(self._last_exc, RtBaseExc):
                            self._last_exc.__record__()
                        else:
                            yield self.CF_RAISE, self._last_exc

                excs = syntactic.If(self.condition, sc_body, sc_else).excs
                if excs.always:
                    yield self.CF_RAISE, RtUnreachable()

            else:
                if self.condition:
                    yield self.CF_IF, None
                    if self._last_exc is not None:
                        yield self.CF_RAISE, self._last_exc
                else:
                    yield self.CF_ELSE, None
                    if self._last_exc is not None:
                        yield self.CF_RAISE, self._last_exc


    def visit_If(self, node):
        """
        if cond:
            {body}
        else:
            {orelse}

        =====>

        for cf, exc in (handler := IfHandler(cond)):
            match cf:
                case IF:
                    with handler.exc_handler():
                        {body}
                case ELSE:
                    with handler.exc_handler():
                        {orelse}
                case RAISE:
                    raise exc
        """
        node = self.generic_visit(node)

        if self._literal_expr_checker.check(node.test):
            return node

        name_cf_var = self.new_name()
        name_handler = self.new_name()
        name_cf_exc = self.new_name()

        new_node = For(
            target=Tuple(
                elts=[
                    Name(id=name_cf_var, ctx=Store()),
                    Name(id=name_cf_exc, ctx=Store())],
                ctx=Store()),
            iter=NamedExpr(
                target=Name(id=name_handler, ctx=Store()),
                value=self.add_call(self.IfHandler, [node.test])),
            body=[
                Match(
                    subject=Name(id=name_cf_var, ctx=Load()),
                    cases=[
                        match_case(
                            **get_pos(node.body),
                            pattern=MatchValue(value=Constant(value=self.IfHandler.CF_IF)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.body if node.body else [Pass()])]),
                        match_case(
                            **get_pos(node.orelse),
                            pattern=MatchValue(value=Constant(value=self.IfHandler.CF_ELSE)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.orelse if node.orelse else [Pass()])]),
                        match_case(
                            **get_pos(node),
                            pattern=MatchValue(value=Constant(value=self.IfHandler.CF_RAISE)),
                            body=[
                                Raise(
                                    exc=Name(id=name_cf_exc, ctx=Load()))])])])

        return new_node

    class ForHandler(ControlFlowHandler):
        CF_FOR = 0
        CF_ELSE = 1
        CF_RAISE = 2

        def __init__(self, iterator: Any):
            super().__init__()
            self.iterator = iterator

        def control_flow(self):
            if is_rt_iterator(self.iterator):
                with enter_scope() as sc_iter:
                    try:
                        item = self.iterator.__next__()
                    except RtBaseExc as e:
                        e.__record__()
                excs_iter = sc_iter.excs.remove(RtStopIteration)
                assert not excs_iter.might, "RtIterator 不能抛出 RtStopIteration 以外的异常。"
                if sc_iter.excs.always:  # 使用 sc_iter 的 exec 避免误判 RtStopIteration
                    # iter 总是抛出异常
                    syntactic.For(self.iterator, sc_iter, Scope(), Scope())
                    return

                with enter_scope() as sc_body:
                    yield self.CF_FOR, item, None
                    if self._last_exc is not None:
                        if isinstance(self._last_exc, RtBaseExc):
                            self._last_exc.__record__()
                        else:
                            yield self.CF_RAISE, None, self._last_exc

                with enter_scope() as sc_else:
                    yield self.CF_ELSE, None, None
                    if self._last_exc is not None:
                        if isinstance(self._last_exc, RtBaseExc):
                            self._last_exc.__record__()
                        else:
                            yield self.CF_RAISE, None, self._last_exc

                excs = syntactic.For(self.iterator, sc_iter, sc_body, sc_else)
                if excs.always:
                    yield self.CF_RAISE, RtUnreachable()
            else:
                for item in self.iterator:
                    yield self.CF_FOR, item, None
                    if self._last_exc is not None:
                        if isinstance(self._last_exc, RtContinue):
                            continue
                        if isinstance(self._last_exc, RtBreak):
                            break
                        yield self.CF_RAISE, None, self._last_exc
                else:
                    yield self.CF_ELSE, None, None
                    if self._last_exc is not None:
                        yield self.CF_RAISE, None, self._last_exc


    def visit_For(self, node):
        """
        for target in iterator:
            {body}
        else:
            {orelse}

        =====>

        for cf, item, exc in (handler := ForHandler(iterator)):
            match cf:
                case FOR:
                    with handler.exc_handler():
                        target = item
                        {body}
                case ELSE:
                    with handler.exc_handler():
                        {orelse}
                case RAISE:
                    raise exc
        """
        node = self.generic_visit(node)

        name_cf_var = self.new_name()
        name_item = self.new_name()
        name_cf_exc = self.new_name()
        name_handler = self.new_name()

        return For(
            target=Tuple(
                elts=[
                    Name(id=name_cf_var, ctx=Store()),
                    Name(id=name_item, ctx=Store()),
                    Name(id=name_cf_exc, ctx=Store())],
                ctx=Store()),
            iter=NamedExpr(
                target=Name(id=name_handler, ctx=Store()),
                value=self.add_call(self.ForHandler, [node.iter])),
            body=[
                Match(
                    subject=Name(id=name_cf_var, ctx=Load()),
                    cases=[
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.ForHandler.CF_FOR)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=[
                                        Assign(
                                            targets=[
                                                node.target],
                                            value=Name(id=name_item, ctx=Load())),
                                        *node.body])]),
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.ForHandler.CF_ELSE)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.orelse if node.orelse else [Pass()])]),
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.ForHandler.CF_RAISE)),
                            body=[
                                Raise(
                                    exc=Name(id=name_cf_exc, ctx=Load()))])])])

    class WhileHandler(ControlFlowHandler):
        CF_COND = 0
        CF_WHILE = 1
        CF_ELSE = 2
        CF_RAISE = 3

        def __init__(self):
            super().__init__()
            self.condition = None
            self.fist_loop = True

        def recv(self, cond):
            self.condition = cond

        def control_flow(self):
            while True:
                yield self.CF_COND, None
                if self.fist_loop and isinstance(self.condition, RtBaseData):
                    self.fist_loop = False
                    with enter_scope() as sc_body:
                        yield self.CF_WHILE, None
                        if self._last_exc is not None:
                            if isinstance(self._last_exc, RtBaseExc):
                                self._last_exc.__record__()
                            elif not is_rt_exception(self._last_exc):
                                yield self.CF_RAISE, self._last_exc

                    with enter_scope() as sc_else:
                        yield self.CF_ELSE, None
                        if self._last_exc is not None:
                            if isinstance(self._last_exc, RtBaseExc):
                                self._last_exc.__record__()
                            elif not is_rt_exception(self._last_exc):
                                yield self.CF_RAISE, self._last_exc

                    excs = syntactic.While(self.condition, sc_body, sc_else).excs
                    if excs.always:
                        yield self.CF_RAISE, RtUnreachable()
                    break
                else:
                    self.fist_loop = False
                    if isinstance(self.condition, RtBaseData):
                        raise TypeError("编译期 while 循环不能使用运行期变量作为判断条件")
                    if self.condition:
                        yield self.CF_WHILE, None
                        if self._last_exc is not None:
                            if isinstance(self._last_exc, RtContinue):
                                yield self.CF_COND, None
                                continue
                            if isinstance(self._last_exc, RtBreak):
                                break
                            yield self.CF_RAISE, self._last_exc
                    else:
                        yield self.CF_ELSE, None
                        if self._last_exc is not None:
                            yield self.CF_RAISE, self._last_exc
                        break

    def visit_While(self, node):
        """
        while condition:
            {body}
        else:
            {orelse}

        =====>

        for cf, exc in (handler := WhileHandler()):
            match cf:
                case COND:
                    handler.recv(condition)
                case WHILE:
                    with handler.exc_handler():
                        {body}
                case ELSE:
                    with handler.exc_handler():
                        {orelse}
                case RAISE:
                    raise exc
        """
        node = self.generic_visit(node)

        name_cf_var = self.new_name()
        name_cf_exc = self.new_name()
        name_handler = self.new_name()

        new_node = For(
            target=Tuple(
                elts=[
                    Name(id=name_cf_var, ctx=Store()),
                    Name(id=name_cf_exc, ctx=Store())],
                ctx=Store()),
            iter=NamedExpr(
                target=Name(id=name_handler, ctx=Store()),
                value=self.add_call(self.WhileHandler, [])),
            body=[
                Match(
                    subject=Name(id=name_cf_var, ctx=Load()),
                    cases=[
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.WhileHandler.CF_COND)),
                            body=[
                                Expr(
                                    value=Call(
                                        func=Attribute(
                                            value=Name(id=name_handler, ctx=Load()),
                                            attr='recv',
                                            ctx=Load()),
                                        args=[
                                            node.test]))]),
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.WhileHandler.CF_WHILE)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.body)]),
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.WhileHandler.CF_ELSE)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.orelse if node.orelse else [ast.Pass()])]),
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.WhileHandler.CF_RAISE)),
                            body=[
                                Raise(
                                    exc=Name(id=name_cf_exc, ctx=Load()))])])])
        return new_node

    class TryHandler(ControlFlowHandler):
        CF_TRY = 0
        CF_ELSE = 1
        CF_FINALLY = 2
        CF_RAISE = 3
        CF_EXCEPT = 10
        def __init__(self, captures : list[type[Exception] | tuple[type[Exception], ...]]):
            super().__init__()
            self.captures: list[tuple[type[Exception]]] = [e if isinstance(e, tuple) else (e,) for e in captures]
            all_exc_types = []
            if len(self.captures) == 0:
                self.is_rt_try = False
            else:
                self.is_rt_try = is_rt_exception(self.captures[0][0])
            for eg in self.captures:
                for et in eg:
                    if self.is_rt_try ^ is_rt_exception(et):
                        raise TypeError("单个 try 语句不能同时捕获编译期异常和运行期异常")
                    all_exc_types.append(et)
            self.all_exc_types = tuple(all_exc_types)

        @staticmethod
        def chain_exc(last: Exception, current: Exception):
            # 设置异常链
            e = current
            while e.__context__ is not None:
                e = e.__context__
            e.__context__ = last

        def control_flow(self):
            if self.is_rt_try:
                with enter_scope() as sc_try:
                    yield self.CF_TRY, None
                    if self._last_exc is not None:
                        if isinstance(self._last_exc, RtBaseExc):
                            self._last_exc.__record__()
                        elif not is_rt_exception(self._last_exc):
                            yield self.CF_RAISE, self._last_exc

                excs_body = sc_try.excs
                for eg in self.captures:
                    excs_body = excs_body.remove_subclasses(eg)

                excepts = []
                handlers_exc = set()

                if excs_body.always:
                    # body 总是抛异常且未被捕获（？）
                    sc_else = Scope()
                else:
                    handled = set()
                    for i, eg in enumerate(self.captures):
                        # 剔除已经被先前 handler 捕获的异常
                        real_eg = []
                        for e in eg:
                            for he in handled:
                                if issubclass(e, he):
                                   break
                            else:
                                real_eg.append(e)
                            handled.add(e)
                            excs_body.remove_subclasses(e)
                        real_eg = tuple(real_eg)

                        if len(real_eg) == 0:
                            continue  # 直接跳过无效的 handler
                        for e in sc_try.excs.set:  # 使用原始 body 异常集判断是否有此类异常抛出
                            if e is not None and issubclass(e, real_eg):
                                break
                        else:
                            continue  # body 不会抛出此类异常，跳过此 handler

                        with enter_scope() as sc_except:
                            yield self.CF_EXCEPT + i, None
                            if self._last_exc is not None:
                                if isinstance(self._last_exc, RtBaseExc):
                                    self._last_exc.__record__()
                                elif not is_rt_exception(self._last_exc):
                                    yield self.CF_RAISE, self._last_exc
                        excepts.append(ExcHandle(eg=real_eg, sc_handle=sc_except))
                        handlers_exc.update(sc_except.excs.set)

                    with enter_scope() as sc_else:
                        if sc_try.excs.always:  # try 总抛出异常则不可能到达 else 块
                            yield self.CF_ELSE, None
                            if self._last_exc is not None:
                                if isinstance(self._last_exc, RtBaseExc):
                                    self._last_exc.__record__()
                                elif not is_rt_exception(self._last_exc):
                                    yield self.CF_RAISE, self._last_exc

                with enter_scope() as sc_finally:
                    yield self.CF_FINALLY, None
                    if self._last_exc is not None:
                        if isinstance(self._last_exc, RtBaseExc):
                            self._last_exc.__record__()
                        elif not is_rt_exception(self._last_exc):
                            yield self.CF_RAISE, self._last_exc

                excs = syntactic.Try(sc_try, excepts, sc_else, sc_finally).excs
                if excs.always:
                    yield self.CF_RAISE, RtUnreachable()
            else:
                exc_body = exc_except = exc_else = exc_finally = None
                # TRY
                yield self.CF_TRY, None
                if self._last_exc is not None:
                    # {body} 出现异常
                    exc_body = self._last_exc

                # EXCEPT
                if exc_body is not None:
                    self._last_exc = None
                    for i, eg in enumerate(self.captures):
                        if isinstance(exc_body, eg):
                            yield self.CF_EXCEPT + i, exc_body
                            exc_except = self._last_exc
                            if exc_except is not None:
                                self.chain_exc(exc_body, exc_except)

                #ELSE
                else:
                    self._last_exc = None
                    yield self.CF_ELSE, None
                    if self._last_exc is not None:
                        # {orelse} 出现异常，先跳转 {finally}
                        exc_else = self._last_exc

                # FINALLY
                self._last_exc = None
                yield self.CF_FINALLY, None
                if self._last_exc is not None:
                    # {finally} 出现异常
                    exc_finally = self._last_exc
                    if isinstance(exc_finally, RtBaseExc):
                        # finally 中的流程控制语句优先执行，同时忽略其他异常
                        exc_finally.__record__()
                        return
                    if (exc_except or exc_else) is not None:
                        self.chain_exc((exc_except or exc_else), exc_finally)
                    yield self.CF_RAISE, exc_finally
                elif exc_else is not None:
                    # {finally} 无异常但 {orelse} 有异常
                    yield self.CF_RAISE, exc_else

    def visit_Try(self, node):
        """
        try:
            {body}
        except type_i as exc_i:
            {handlerbody_i}
        else:
            {orelse}
        finally:
            {finallybody}

        =====>

        for cf, exc in (handler := TryHandler([type_i])):
            match cf:
                case TRY:
                    with handler.exc_handler():
                        {body}
                case EXCEPT_i:
                    exc_i = exc
                    with handler.exc_handler():
                        {handlerbody_i}
                    del exc_i
                case ELSE:
                    with handler.exc_handler():
                        {orelse}
                case FINALLY:
                    with handler.exc_handler():
                        {finallybody}
                case RAISE:
                    raise exc
        """
        node = self.generic_visit(node)

        name_cf_var = self.new_name()
        name_cf_exc = self.new_name()
        name_handler = self.new_name()

        handlers = []

        for i, h in enumerate(node.handlers):
            body = [
                With(
                    items=[
                        withitem(
                            context_expr=Call(
                                func=Attribute(
                                    value=Name(id=name_handler, ctx=Load()),
                                    attr='exc_handler',
                                    ctx=Load())))],
                    body=h.body),
            ]
            if h.name is not None:
                body = [
                    Assign(
                        targets=[
                            Name(id=h.name, ctx=Store())],
                        value=Name(id=name_cf_exc, ctx=Load())),
                    * body,
                    Delete(
                        targets=[
                            Name(id=h.name, ctx=Del())]),
                ]
            handlers.append(
                match_case(
                    pattern=MatchValue(value=Constant(value=self.TryHandler.CF_EXCEPT + i)),
                    body=body)
            )

        new_node = For(
            target=Tuple(
                elts=[
                    Name(id=name_cf_var, ctx=Store()),
                    Name(id=name_cf_exc, ctx=Store())],
                ctx=Store()),
            iter=NamedExpr(
                target=Name(id=name_handler, ctx=Store()),
                value=self.add_call(self.TryHandler, [List(elts=[h.type for h in node.handlers])])),
            body=[
                Match(
                    subject=Name(id=name_cf_var, ctx=Load()),
                    cases=[
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.TryHandler.CF_TRY)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.body)]),
                        *handlers,
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.TryHandler.CF_ELSE)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.orelse if node.orelse else [Pass()])]),
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.TryHandler.CF_FINALLY)),
                            body=[
                                With(
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=Attribute(
                                                    value=Name(id=name_handler, ctx=Load()),
                                                    attr='exc_handler',
                                                    ctx=Load())))],
                                    body=node.finalbody if node.finalbody else [Pass()])]),
                        match_case(
                            pattern=MatchValue(value=Constant(value=self.TryHandler.CF_RAISE)),
                            body=[
                                Raise(
                                    exc=Name(id=name_cf_exc, ctx=Load()))])])])
        return new_node

    @staticmethod
    def handle_ifexp(condition, br_if, br_else):
        if isinstance(condition, RtBaseData):
            v_if = v_else = None
            with enter_scope() as sc_body:
                try:
                    v_if = br_if()
                except RtBaseExc as e:
                    e.__record__()
            with enter_scope() as sc_else:
                try:
                    v_else = br_if()
                except RtBaseExc as e:
                    e.__record__()
            if isinstance(v_if, RtBaseData):
                res = v_if.__create_tmp__()
            elif isinstance(v_else, RtBaseData):
                res = v_else.__create_tmp__()
            else:
                raise TypeError(f"运行期 if 表达式至少有一方的值为运行期量，得到 {v_if!r}, {v_else!r}")
            with enter_scope(sc_body):
                res.__assign__(v_if)
            with enter_scope(sc_else):
                res.__assign__(v_else)

            excs = syntactic.If(condition, sc_body, sc_else).excs
            if excs.always:
                raise RtUnreachable()
            return res
        else:
            return br_if() if condition else br_else()

    def visit_IfExp(self, node):
        """
        a if b else c

        =====>

        handle_ifexp(b, lambda: a, lambda: c)
        """
        node = self.generic_visit(node)

        return self.add_call(
                func=self.handle_ifexp,
                args=[
                    node.test,
                    Lambda(
                        args=arguments(),
                        body=node.body),
                    Lambda(
                        args=arguments(),
                        body=node.orelse)])

    @staticmethod
    def handle_and(*values):
        r = values[0]
        for v in values[1:]:
            if isinstance(r, RtBaseData) or isinstance(v, RtBaseData):
                if hasattr(r, "__bool_and__"):
                    try:
                        r = r.__bool_and__(v)
                        continue
                    except NotImplementedError:
                        pass
                if hasattr(v, "__bool_and__"):
                    try:
                        r = v.__bool_and__(r)
                        continue
                    except NotImplementedError:
                        pass
                raise TypeError(f"unsupported operand type(s) for 'and': {r.__class__.__name__!r} and {v.__class__.__name__!r}")
            else:
                r = r and v
        return r

    @staticmethod
    def handle_or(*values):
        r = values[0]
        for v in values[1:]:
            if isinstance(r, RtBaseData) or isinstance(v, RtBaseData):
                if hasattr(r, "__bool_or__"):
                    tmp = r.__bool_or__(v)
                    if tmp is not NotImplemented:
                        r = tmp
                        continue
                if hasattr(v, "__bool_or__"):
                    tmp = v.__bool_or__(r)
                    if tmp is not NotImplemented:
                        r = tmp
                        continue
                raise TypeError(
                    f"unsupported operand type(s) for 'or': {r.__class__.__name__!r} and {v.__class__.__name__!r}")
            else:
                r = r or v
        return r

    def visit_BoolOp(self, node):
        """
        a <op> b <op> ...

        =====>

        handler(a, b, ...)
        """
        node = self.generic_visit(node)

        match node.op:
            case And():
                handler = self.handle_and
            case Or():
                handler = self.handle_or
            case _:
                raise
        return self.add_call(handler, *node.values)


    # def visit_Assign(self, node):
    #     """
    #     target = value
    #
    #     =====>
    #
    #     tmp_value = value
    #     try:
    #         tmp_target = target
    #     except Exception:
    #         target = tmp_value
    #     else:
    #         if not assign_handler(tmp_target, tmp_value):
    #             target = tmp_value
    #
    #     =============
    #
    #     target_i, ... = value
    #
    #     =====>
    #
    #
    #
    #     =============
    #
    #     target1, *target2, target3 = value
    #
    #     带 * 的赋值只能在所有左值均是编译期量时进行，以保证行为一致性
    #
    #     """
    #     node = self.generic_visit(node)
    #
    #     targets = node.targets






    def visit_Continue(self, node):
        """
        continue

        =====>

        raise CtContinue()
        """
        return Raise(exc=self.add_call(RtContinue, []))

    def visit_Break(self, node):
        """
        break

        =====>

        raise CtBreak()
        """
        return Raise(exc=self.add_call(RtBreak, []))

    def visit_Return(self, node):
        """
        return value

        =====>

        raise CtReturn(value)
        """
        return Raise(exc=self.add_call(RtReturn, [node.value if node.value is not None else Constant(None)]))

    @staticmethod
    def raw_handler(code, note=None):
        syntactic.Raw(code=code)

    def visit_Expr(self, node):
        node = self.generic_visit(node)

        if isinstance(node.value, JoinedStr):
            # 野生 fstr 处理为 Raw
            return Expr(
                value=self.add_call(self.raw_handler, [node.value])
            )
        elif isinstance(node.value, Subscript) and isinstance(node.value.value, JoinedStr):
            # 带切片的野生 fstr 处理为 Raw + note
            return Expr(
                value=self.add_call(self.raw_handler, [node.value.value, node.value.slice])
            )
        else:
            return node

    def visit_FunctionDef(self, node):
        # 不改写内嵌函数
        return node

    def visit_AsyncFunctionDef(self, node):
        # 不改写内嵌异步函数
        return node

    def visit_ClassDef(self, node):
        # 不改写内嵌类
        return node

    def visit_Call(self, node):
        # Call 操作在运行期函数被调用时生成，此处不作任何额外处理
        return super().generic_visit(node)


def reform_func(func: FunctionType) -> FunctionType:
    """
    将 python 函数改造为 ast 生成器

    生成器调用参数与原函数相同，返回值为生成的 Context
    """
    lines, start_line = inspect.getsourcelines(func)

    if lines[0].startswith((' ', '\t')):  # 判断函数定义是否存在整体缩进
        """
        不能随意删除缩进，否则可能导致多行字符串的内容发生改变。
        此处将函数定义包裹在 if 内部使语法解析正确进行。
        """
        lines.insert(0, "if True:\n")
        start_line -= 1
        code = "".join(lines)
        node = parse(code, mode='exec')
        node = node.body[0].body[0]
    else:
        code = "".join(lines)
        node = parse(code, mode='exec')
        node = node.body[0]

    node = increment_lineno(node, start_line - 1)
    rewriter = ASTRewriter(wrapper_name="$wrapper")
    node = rewriter.rewrite(node)
    node = fix_missing_locations(node)

    glb = func.__globals__
    glb_ext = rewriter.get_glb()
    glb.update(glb_ext)
    exec(compile(node, inspect.getfile(func), 'exec'), glb)
    wrapper = glb["$wrapper"]
    new_func = wrapper()

    del glb["$wrapper"]
    for k in glb_ext:
        del glb[k]

    return new_func

