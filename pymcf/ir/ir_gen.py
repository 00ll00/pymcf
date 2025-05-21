import ast
from ast import NodeVisitor
from collections import defaultdict
from typing import Any, Callable

from pymcf.config import Config
from .codeblock import BasicBlock, MatchJump, JmpEq, code_block
from pymcf.ast_ import operation, Context, Scope, compiler_hint, If, For, Try, Call, RtBaseExc, \
    RtStopIteration, RtContinue, RtBreak, Assign, Raise, While


class IrCfg(Config):

    ir_inline_catch: bool = True
    """
    是否进行异常处理的内联化
    
    若启用，在条满足时会将异常产生后的逻辑重定位到其应当被捕获的块，进而省略标志判断的流程。内联不影响异常栈的构建。
    """

    ir_set_bf: Callable[[Any], None]

    ir_clear_bf: Callable

    ir_simplify: int = 3
    """
    应用 IR 流程简化算法的迭代次数。
    """


class Expander(NodeVisitor):

    def __init__(self, scope: Scope, break_flag: Any, config: IrCfg, root_name: str = "root"):
        self.scope = scope
        self.root = BasicBlock(root_name)
        self.config = config
        self.cb_stack: list[BasicBlock] = [self.root]
        self.bf = break_flag

        self.inline_catch = config.ir_inline_catch and self.can_inline_catch()
        if self.inline_catch:
            self._exc_handler_in: list[tuple[tuple[type[RtBaseExc], ...] | None, code_block]] = []
            self._try_match_jump: list[code_block] = []

    def clear_flag_op(self) -> operation:
        return Assign(self.bf, 0, _offline=True)

    def set_flag_op(self, flag: Any) -> operation:
        return Assign(self.bf, flag, _offline=True)

    def add_op(self, op: operation | compiler_hint):
        self.current_block().ops.append(op)

    def can_inline_catch(self) -> bool:
        # 存在不为空的 finally 块时无法进行异常内联
        for node in ast.walk(self.scope):
            if isinstance(node, Try):
                if len(node.sc_finally.flow) > 0:
                    return False
        return True

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

    def push_exc_handler(self, eg: tuple[type[RtBaseExc], ...] | None, cb_in: code_block):
        if self.inline_catch:
            self._exc_handler_in.append((eg, cb_in))

    def pop_exc_handler(self):
        if self.inline_catch:
            self._exc_handler_in.pop()

    def push_try_match(self, cb: code_block):
        if self.inline_catch:
            self._try_match_jump.append(cb)

    def pop_try_match(self):
        if self.inline_catch:
            self._try_match_jump.pop()

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

        if not self.inline_catch and node.sc_body.excs.might:
            if not node.sc_body.excs.always:
                cb_body_out.cond = self.bf
                cb_body_out.false = cb_next_in
        else:
            cb_body_out.direct = cb_next_in

        if not self.inline_catch and  node.sc_else.excs.might:
            if not node.sc_else.excs.always:
                cb_else_out.cond = self.bf
                cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in

    def visit_For(self, node: For):
        cb_last_out = self.exit_block()

        cb_else_in = self.enter_block(name="for_else")
        self.visit(node.sc_else)
        cb_else_out = self.exit_block()

        cb_iter_in = self.enter_block(name="for_iter")
        self.push_exc_handler((RtStopIteration,), cb_else_in)
        self.visit(node.sc_iter)
        self.pop_exc_handler()
        cb_iter_out = self.exit_block()

        cb_next_in = self.enter_block(name="for_next")

        cb_body_in = self.enter_block(name="for_body")
        self.push_exc_handler((RtContinue,), cb_iter_in)
        self.push_exc_handler((RtBreak,), cb_next_in)
        # self.add_op(self.clear_flag_op()) #  进入 body 时清空 bf  TODO bf 的清理方式
        self.visit(node.sc_body)
        self.pop_exc_handler()
        self.pop_exc_handler()
        cb_body_out = self.exit_block()

        cb_catch_iter = BasicBlock(name="for_catch_iter")
        cb_catch_body = BasicBlock(name="for_catch_body")

        cb_iter = cb_catch_iter if not self.inline_catch and node.sc_iter.excs.might else cb_iter_in
        cb_body = cb_catch_body if not self.inline_catch and node.sc_body.excs.might else cb_body_in

        if not self.inline_catch and node.sc_iter.excs.might:
            cb_last_out.direct = cb_catch_iter
            cb_catch_iter.direct = cb_iter_in

            if node.sc_iter.excs.always:
                cb_catch_iter.direct = cb_else_in
            else:
                cb_catch_iter.cond = self.bf  # TODO iter 中是否需要允许抛出 RtStopIteration 以外的异常
                cb_catch_iter.false = cb_body
                cb_catch_iter.true = cb_else_in  # TODO 清理异常标志
        else:
            cb_last_out.direct = cb_iter_in
            cb_iter_out.direct = cb_body

        if not self.inline_catch and node.sc_body.excs.might:
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

        if not self.inline_catch and node.sc_else.excs.might:
            if not node.sc_else.excs.always:
                cb_else_out.cond = self.bf
                cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in


    def visit_While(self, node: While):
        cb_last_out = self.exit_block()

        cb_next_in = self.enter_block(name="while_next")

        cb_body_in = self.enter_block(name="while_body")
        self.push_exc_handler((RtContinue,), cb_body_in)
        self.push_exc_handler((RtBreak,), cb_next_in)
        self.visit(node.sc_body)
        self.pop_exc_handler()
        self.pop_exc_handler()
        cb_body_out = self.exit_block()

        cb_else_in = self.enter_block(name="while_else")
        self.visit(node.sc_else)
        cb_else_out = self.exit_block()

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

        if not self.inline_catch and node.sc_else.excs.might:
            if not node.sc_else.excs.always:
                cb_else_out.cond = self.bf
                cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in


    def visit_Try(self, node: Try):
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
            # cb_exc_in.add_op(self.clear_flag_op())  # TODO
            self.visit(exc_handler.sc_handle)
            cb_exc_out = self.exit_block()
            cb_exc_out.direct = cb_finally_in
            cb_excepts.append((cb_exc_in, exc_handler.eg, captures))

        cb_else_in = self.enter_block(name="try_else")
        self.visit(node.sc_else)
        cb_else_out = self.exit_block()

        cb_jump = MatchJump(self.bf, [
            JmpEq(eg, cb_exc_in) for cb_exc_in, eg, captures in cb_excepts if len(captures) > 0
        ], inactive=0, name="try_jump")

        if self.inline_catch:
            # inline catch 时级联异常处理块
            cb_catch.direct = cb_jump
            if self._try_match_jump:
                cb_catch.cond = self.bf
                cb_catch.true = self._try_match_jump[-1]

        self.push_try_match(cb_catch)

        cb_body_in = self.enter_block(name="try_body")
        for cb_exc_in, eg, _ in cb_excepts[::-1]:
            self.push_exc_handler(eg, cb_exc_in)
        self.visit(node.sc_try)
        for _ in range(len(cb_excepts)):
            self.pop_exc_handler()
        cb_body_out = self.exit_block()

        self.pop_try_match()

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

        cb_else_out.direct = cb_finally_in

        # TODO 处理 finally 异常覆盖问题
        if self.inline_catch:
            assert not node.sc_finally.excs.might, "启用 ir_inline_catch 时 finally 块不能存在呈递流程控制语句（continue, break, return 或抛出异常）"
            cb_finally_out.direct = cb_next_in
        else:
            if not node.sc_finally.excs.always:
                if node.sc_else.excs.might or node.sc_finally.excs.might or any(h.sc_handle.excs.might for h in node.excepts):
                    cb_finally_out.cond = self.bf
                    cb_finally_out.false = cb_next_in
                else:
                    # exception_handlers, else, finally 均不会抛出异常，则可以直接跳转
                    cb_finally_out.direct = cb_next_in

    def visit_Raise(self, node: Raise):
        # TODO err stack
        if not self.inline_catch:
            self.current_block().add_op(self.set_flag_op(node.exc_class))
        else:
            cb_last_out = self.exit_block()
            for eg, handler in self._exc_handler_in[::-1]:
                if issubclass(node.exc_class, eg):
                    cb_last_out.direct = handler
                    break
            else:
                cb_last_out.add_op(self.set_flag_op(node.exc_class))
            self.enter_block(name="AFTER_RAISE")

    def visit_Call(self, node: Call):
        self.current_block().add_op(node)
        if node.excs.might:
            cb_last = self.exit_block()
            cb_next = self.enter_block(name="call_next")
            cb_last.cond = self.bf
            cb_last.false = cb_next
            if self.inline_catch and self._try_match_jump:
                cb_last.true = self._try_match_jump[-1]


def control_flow_expand(scope: Scope, break_flag: Any, config: IrCfg, root_name: str = "root") -> code_block:
        expander =Expander(scope, break_flag=break_flag, config=config, root_name=root_name)
        expander.expand()
        return expander.root


class CBSimplifier:

    def __init__(self):
        self.visited = {}
        self.simplified = False

    def mark_simplified(self):
        self.simplified = True

    def simplify(self, node: code_block):
        self.visited = self.visited
        if id(node) in self.visited:
            return self.visited[id(node)]
        if isinstance(node, BasicBlock):
            self.visited[id(node)] = self.simplify_BasicBlock(node)
        elif isinstance(node, MatchJump):
            self.visited[id(node)] = self.simplify_MatchJump(node)
        else:
            self.visited[id(node)] = node
        for name, field in ast.iter_fields(node):
            if isinstance(field, code_block):
                setattr(node, name, self.simplify(field))
            elif isinstance(field, list):
                for item in field:
                    self.simplify(item)
            elif isinstance(field, ast.AST):
                self.simplify(field)
        return self.visited[id(node)]

    def simplify_BasicBlock(self, cb: BasicBlock) -> code_block | None:
        return cb

    def simplify_MatchJump(self, cb: MatchJump) -> code_block | None:
        return cb


class EmptyCBRemover(CBSimplifier):
    """
    消除空块和简化跳转逻辑
    """
    def simplify_BasicBlock(self, cb: BasicBlock) -> BasicBlock | None:
        if cb.true is None and cb.false is None:
            cb.cond = None
            self.mark_simplified()
        elif cb.cond is None:
            cb.true = cb.false = None
            self.mark_simplified()

        if cb.cond is None and isinstance(cb.direct, BasicBlock) and len(cb.direct.ops) == 0:
            # 当前块直接跳转空块且无条件跳转，将空块的跳转方式提前
            cb.cond = cb.direct.cond
            cb.false = cb.direct.false
            cb.true = cb.direct.true
            cb.direct = cb.direct.direct
            self.mark_simplified()
        if len(cb.ops) == 0 and cb.cond is None:
            # 不应存在全空的环路
            self.mark_simplified()
            return cb.direct
        if cb.cond is not None:
            # 跳过相同条件的空块
            if isinstance(cb.true, BasicBlock) and cb.true.cond is cb.cond and len(cb.true.ops) == 0 and cb.true.direct is None:
                cb.true = cb.true.true
                self.mark_simplified()
            if isinstance(cb.false, BasicBlock) and cb.false.cond is cb.cond and len(cb.false.ops) == 0 and cb.false.direct is None:
                cb.false = cb.false.false
                self.mark_simplified()
        return cb

    def simplify_MatchJump(self, cb: MatchJump) -> MatchJump | None:
        if len(cb.cases) == 0:
            self.mark_simplified()
            return None
        # 无跳转目标的case暂时不能删除，可能存在flag清除的作用
        return cb


class CBInliner(CBSimplifier):

    def __init__(self, root: code_block):
        super().__init__()
        self.node_ref = defaultdict(int)
        def count_ref(node):
            for name, field in ast.iter_fields(node):
                if isinstance(field, code_block):
                    self.node_ref[id(field)] += 1
                    if self.node_ref[id(field)] == 1:
                        count_ref(field)
                elif isinstance(field, list):
                    for item in field:
                        self.node_ref[id(item)] += 1
                        if self.node_ref[id(item)] == 1:
                            count_ref(item)



    def simplify_BasicBlock(self, cb: BasicBlock) -> BasicBlock | None:
        ...




def simplify(root: code_block, config: IrCfg) -> code_block | None:
    for _ in range(config.ir_simplify):
        simplifier = EmptyCBRemover()
        root = simplifier.simplify(root)
        if root is None:
            return None
        if not simplifier.simplified:
            break
    return root

class Compiler:

    def compile(self, ctx: Context) -> BasicBlock:
        ...