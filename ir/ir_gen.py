import ast
from ast import NodeVisitor, NodeTransformer
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, NamedTuple, Protocol, Callable

from config import Config
from .codeblock import BasicBlock, MatchJump, JmpEq, code_block, JmpNeq
from ast_ import operation, Context, Scope, compiler_hint, If, For, Try, Call, RtBaseExc, \
    RtStopIteration, RtContinue, RtBreak, Assign, Raise, While, ExcHandle, stmt, ExcSet, AST


class IrCfg(Config):

    ir_inline_catch: bool = True
    """
    是否进行异常处理的内联化
    
    若启用，会将异常产生后的逻辑重定位到其应当被捕获的块，进而省略标志判断的流程。内联不影响异常栈的构建。
    """

    ir_set_bf: Callable[[Any], None]

    ir_clear_bf: Callable

    ir_simplify: int = 3
    """
    应用 IR 流程简化算法的迭代次数。
    """


class InlinedRaise(stmt):
    """
    被内联的 Raise
    """
    excs = ExcSet.EMPTY
    _fields = ("origin", )  # target_handler 不算 field，避免扰乱树结构

    def __init__(self, origin: Raise, *args, **kwargs):
        self.origin = origin
        self.cb_out = None
        super().__init__(*args, **kwargs)


class CatchedCall(stmt):
    """
    内联异常处理的 Call，
    """
    _fields = ("origin", )
    def __init__(self, origin: Call, remain_excs: ExcSet, *args, **kwargs):
        self.origin = origin
        self.remain_excs = remain_excs
        self.cb_out = None
        super().__init__(*args, **kwargs)

    @property
    def excs(self) -> ExcSet:
        return self.remain_excs


class _CatchInliner(NodeTransformer):

    def __init__(self, config: IrCfg):
        self.config = config
        self.handler_stack: list[tuple[stmt, tuple[type[RtBaseExc], ...]]] = []
        self.handled_raise: dict[stmt, list[InlinedRaise]] = defaultdict(list)

    def visit(self, node):
        # 重新计算各节点的 excs
        node = super().visit(node)
        if isinstance(node, AST):
            node.clear_cache()
        return node

    def visit_Try(self, node: Try):
        catches = set()
        for handler in node.excepts:
            catches.update(handler.eg)
        catches = tuple(catches)
        self.handler_stack.append((node, catches))
        node = self.generic_visit(node)
        self.handler_stack.pop()
        return node

    def visit_For(self, node: For):
        # Iter 的异常不在此次处理
        self.handler_stack.append((node, (RtContinue, RtBreak)))
        node = self.generic_visit(node)
        self.handler_stack.pop()
        return node

    def visit_While(self, node: While):
        self.handler_stack.append((node, (RtContinue, RtBreak)))
        node = self.generic_visit(node)
        self.handler_stack.pop()
        return node

    def visit_Raise(self, node: Raise):
        exc = node.exc_class
        inlined_handler = None
        for capture_stmt, catches in self.handler_stack[::-1]:
            if issubclass(exc, catches):
                inlined_handler = capture_stmt
        if inlined_handler is not None:
            new_node = InlinedRaise(node, _offline=True)
            self.handled_raise[inlined_handler].append(new_node)
            return new_node
        return node

    def visit_Call(self, node: Call):
        excs = node.excs
        for _, eg in self.handler_stack:
            excs = excs.remove_subclasses(eg)
        return CatchedCall(node, excs, _offline=True)


class _Expander(NodeVisitor):

    def __init__(self, scope: Scope, break_flag: Any, config: IrCfg):
        self.scope = scope
        self.root = BasicBlock("root")
        self.config = config
        self.cb_stack: list[BasicBlock] = [self.root]
        self.bf = break_flag

        self.inline_catch = config.ir_inline_catch

        # 用于 try inline
        if self.inline_catch:
            self._catch_inliner = _CatchInliner(config)
            self.scope = self._catch_inliner.visit(self.scope)
            self._cb_handler_in = {}
            self._try_jump_stack = []

    def clear_flag_op(self) -> operation:
        return Assign(self.bf, 0, _offline=True)

    def set_flag_op(self, flag: Any) -> operation:
        return Assign(self.bf, flag, _offline=True)

    def add_op(self, op: operation | compiler_hint):
        self.current_block().ops.append(op)

    def enter_block(self, cb: BasicBlock=None, name: str = None) -> BasicBlock:
        if cb is None:
            assert name is not None
            cb = BasicBlock(name)
        self.cb_stack.append(cb)
        return cb

    def exit_block(self) -> BasicBlock:
        return self.cb_stack.pop()

    def current_block(self) -> BasicBlock:
        return self.cb_stack[-1]

    def expand(self) -> BasicBlock:
        """
        将 self.scope 展开为 CodeBlock
        :return: 根节点 block
        """
        self.visit(self.scope)
        assert len(self.cb_stack) == 1
        return self.root

    def visit_Scope(self, node: Scope):
        super().generic_visit(node)

    def generic_visit(self, node: Any) -> Any:
        if isinstance(node, operation):
            self.current_block().add_op(node)

    def visit_If(self, node: If):
        cb_last_out = self.exit_block()

        cb_body_in = self.enter_block(name="if_body")
        self.visit(node.sc_body)
        cb_body_out = self.exit_block()

        cb_else_in = self.enter_block(name="if_else")
        self.visit(node.sc_else)
        cb_else_out = self.exit_block()

        cb_last_out.cond = node.condition
        cb_last_out.true = cb_body_in
        cb_last_out.false = cb_else_in

        cb_next_in = self.enter_block(name="if_next")

        if node.sc_body.excs.might:
            cb_body_out.cond = self.bf
            cb_body_out.false = cb_next_in
        else:
            cb_body_out.direct = cb_next_in

        if node.sc_else.excs.might:
            cb_else_out.cond = self.bf
            cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in

    def visit_For(self, node: For):
        cb_last_out = self.exit_block()

        cb_iter_in = self.enter_block(name="for_iter")
        self.visit(node.sc_iter)
        cb_iter_out = self.exit_block()

        cb_body_in = self.enter_block(name="for_body")
        # self.add_op(self.clear_flag_op()) #  进入 body 时清空 bf  TODO bf 的清理方式
        self.visit(node.sc_body)
        cb_body_out = self.exit_block()

        cb_else_in = self.enter_block(name="for_else")
        self.visit(node.sc_else)
        cb_else_out = self.exit_block()

        cb_next_in = self.enter_block(name="for_next")

        cb_catch_iter = BasicBlock(name="for_catch_iter")
        cb_catch_body = BasicBlock(name="for_catch_body")

        cb_iter = cb_catch_iter if node.sc_iter.excs.might else cb_iter_in
        cb_body = cb_catch_body if node.sc_body.excs.might else cb_body_in

        if not self.inline_catch and node.sc_iter.excs.might:
            cb_last_out.direct = cb_catch_iter
            cb_catch_iter.direct = cb_iter_in

            cb_catch_iter.cond = self.bf  # TODO iter 中是否需要允许抛出 RtStopIteration 以外的异常
            cb_catch_iter.false = cb_body
            cb_catch_iter.true = cb_else_in  # TODO 清理异常标志
        else:
            cb_last_out.direct = cb_iter_in
            cb_iter_out.direct = cb_body

            if self.inline_catch and node in self._catch_inliner.handled_raise:
                for r in self._catch_inliner.handled_raise[node]:
                    if r.origin.exc_class is RtContinue:
                        r.cb_out.direct = cb_iter_in
                    elif r.origin.exc_class is RtBreak:
                        r.cb_out.direct = cb_next_in
                    else:
                        raise TypeError

        if node.sc_body.excs.might:
            cb_jump = MatchJump(self.bf, [
                # JmpEq(RtStopIteration, cb_else_in),  # TODO for 的 iterator 是否只允许抛出 RtStopIteration
                JmpEq(RtContinue, cb_iter_in),
                JmpEq(RtBreak, cb_next_in),
            ], inactive=0, name="for_jump")

            cb_catch_body.direct = cb_body_in
            cb_catch_body.cond = self.bf
            cb_catch_body.false = cb_iter
            cb_catch_body.true = cb_jump
        else:
            cb_body_out.direct = cb_iter

        if node.sc_else.excs.might:
            cb_else_out.cond = self.bf
            cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in


    def visit_While(self, node: While):
        cb_last_out = self.exit_block()

        cb_body_in = self.enter_block(name="while_body")
        self.visit(node.sc_body)
        cb_body_out = self.exit_block()

        cb_else_in = self.enter_block(name="while_else")
        self.visit(node.sc_else)
        cb_else_out = self.exit_block()

        cb_next_in = self.enter_block(name="while_next")

        if not self.inline_catch and node.sc_body.excs.might:
            cb_test = BasicBlock(name="while_test")
            cb_catch = BasicBlock(name="while_catch")
            cb_jump = MatchJump(self.bf, [
                JmpEq(RtContinue, cb_test),
                JmpEq(RtBreak, cb_next_in),
            ], inactive=0, name="while_jump")

            cb_test.cond = node.condition
            cb_test.true = cb_catch
            cb_test.false = cb_else_in

            cb_body_out.direct = cb_test

            # cb_next_in.add_op(self.clear_flag_op())  # TODO
            # cb_test.add_op(self.clear_flag_op())

            cb_catch.direct = cb_body_in
            cb_catch.cond = self.bf
            cb_catch.true = cb_jump

            cb_last_out.direct = cb_test
        else:
            cb_last_out.cond = node.condition
            cb_last_out.true = cb_body_in
            cb_last_out.false = cb_else_in

            cb_body_out.cond = node.condition
            cb_body_out.true = cb_body_in
            cb_body_out.false = cb_else_in

            if self.inline_catch and node in self._catch_inliner.handled_raise:
                for r in self._catch_inliner.handled_raise[node]:
                    if r.origin.exc_class is RtContinue:
                        r.cb_out.direct = cb_body_in
                    elif r.origin.exc_class is RtBreak:
                        r.cb_out.direct = cb_next_in
                    else:
                        raise TypeError


        if node.sc_else.excs.might:
            cb_else_out.cond = self.bf
            cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in


    def visit_Try(self, node: Try):  # TODO 内联Call
        cb_last_out = self.exit_block()

        cb_catch = BasicBlock(name="try_catch")

        cb_finally_in = self.enter_block(name="try_finally")
        self.visit(node.sc_finally)
        cb_finally_out = self.exit_block()

        # 优先于 body 构造 handler 块，使 InlinedRaise 能够识别对应的块
        cb_excepts = []
        for exc_handler in node.excepts:
            captures =set()
            for e in node.sc_try.excs.set:
                if e is not None and issubclass(e, exc_handler.eg):
                    captures.add(e)

            cb_exc_in = self.enter_block(name="try_except")
            if self.inline_catch:
                self._cb_handler_in[exc_handler] = cb_exc_in
            # cb_exc_in.add_op(self.clear_flag_op())  # TODO
            self.visit(exc_handler.sc_handle)
            cb_exc_out = self.exit_block()
            cb_exc_out.direct = cb_finally_in
            cb_excepts.append((cb_exc_in, exc_handler.eg, captures))

        cb_jump = MatchJump(self.bf, [
            JmpEq(eg, cb_exc_in) for cb_exc_in, eg, captures in cb_excepts if len(captures) > 0
        ], inactive=0, name="try_jump")

        if self.inline_catch:
            self._try_jump_stack.append(cb_jump)

        cb_body_in = self.enter_block(name="try_body")
        self.visit(node.sc_try)
        cb_body_out = self.exit_block()

        if self.inline_catch:
            self._try_jump_stack.pop()

        cb_else_in = self.enter_block(name="try_else")
        self.visit(node.sc_else)
        cb_else_out = self.exit_block()

        cb_next_in = self.enter_block(name="try_next")

        if not self.inline_catch and node.sc_try.excs.might:
            cb_last_out.direct = cb_catch

            cb_catch.direct = cb_body_in
            cb_catch.cond = self.bf
            cb_catch.false = cb_else_in
            cb_catch.true = cb_jump
        else:
            cb_last_out.direct = cb_body_in
            cb_body_out.direct = cb_else_in

            if self.inline_catch and self._try_jump_stack:
                cb_jump.cases.append(JmpNeq(0, self._try_jump_stack[-1]))


        # TODO 处理 finally 异常覆盖问题
        cb_else_out.direct = cb_finally_in

        cb_finally_out.cond = self.bf
        cb_finally_out.false = cb_next_in


    def visit_Raise(self, node: Raise):
        # TODO err stack
        self.current_block().add_op(self.set_flag_op(node.exc_class))
        self.exit_block()
        self.enter_block(name="AFTER_RAISE")

    def visit_InlinedRaise(self, node: InlinedRaise):
        # TODO err stack
        cb_last_out = self.exit_block()
        node.cb_out = cb_last_out
        self.enter_block(name="AFTER_INLINED_RAISE")


    def visit_Call(self, node: Call):
        self.current_block().add_op(node)
        cb_last = self.exit_block()
        cb_next = self.enter_block(name="call_next")
        cb_last.cond = self.bf
        cb_last.false = cb_next

    def visit_CatchedCall(self, node: CatchedCall):
        assert self.inline_catch
        self.current_block().add_op(node.origin)
        cb_last = self.exit_block()
        cb_next = self.enter_block(name="call_next")
        cb_last.cond = self.bf
        cb_last.false = cb_next
        if self._try_jump_stack:
            cb_last.true = self._try_jump_stack[-1]


def control_flow_expand(scope: Scope, break_flag: Any, config: IrCfg) -> code_block:
        expander =_Expander(scope, break_flag=break_flag, config=config)
        expander.expand()
        return expander.root


def _simplify(root: code_block) -> code_block:
    # TODO 单次 simplify 无法完全消除冗余节点
    visited = {}

    def visit(node: code_block):
        if id(node) in visited:
            return visited[id(node)]
        if isinstance(node, code_block):
            visited[id(node)] = node.simplified()
        else:
            visited[id(node)] = node
        for name, field in ast.iter_fields(node):
            if isinstance(field, code_block):
                setattr(node, name, visit(field))
            elif isinstance(field, list):
                for item in field:
                    visit(item)
            elif isinstance(field, ast.AST):
                visit(field)

        return visited[id(node)]


    return visit(root)


def simplify(root: code_block, config: IrCfg) -> code_block:
    for _ in range(config.ir_simplify):
        root = _simplify(root)
    return root

class Compiler:

    def compile(self, ctx: Context) -> BasicBlock:
        ...