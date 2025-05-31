import ast
from ast import NodeVisitor
from collections import defaultdict
from typing import Any, Callable, Generator

from pymcf.config import Config
from .codeblock import BasicBlock, MatchJump, JmpEq, code_block, IrBlockAttr
from pymcf.ast_ import operation, Constructor, Block, compiler_hint, If, For, Try, Call, RtBaseExc, \
    RtStopIteration, RtContinue, RtBreak, Assign, Raise, While, RtBaseVar, Scope, With
from ..ast_.runtime import RtReturn


class IrCfg(Config):

    ir_inline_catch: bool = True
    """
    是否进行异常处理的内联化
    
    若启用，在条满足时会将异常产生后的逻辑重定位到其应当被捕获的块，进而省略标志判断的流程。内联不影响异常栈的构建。
    """

    ir_inline_thresh: int = 32
    """
    允许内联的块的操作数阈值。单引用无条件跳转块只有在值小于 0 时禁用内联。
    """

    ir_set_bf: Callable[[Any], None]

    ir_clear_bf: Callable

    ir_simplify: int = 3
    """
    应用 IR 流程简化算法的迭代次数。
    """

    ir_bf: RtBaseVar


class Expander(NodeVisitor):

    def __init__(self, block: Block, break_flag: Any, config: IrCfg, root_name: str = "root"):
        self.block = block
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
        for node in ast.walk(self.block):
            if isinstance(node, Try):
                if len(node.blk_finally.flow) > 0:
                    return False
            elif isinstance(node, With):
                if len(node.blk_exit.flow) > 0:
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
        将 self.block 展开为 CodeBlock
        :return: 根节点 block
        """
        self.visit(self.block)
        assert len(self.cb_stack) == 1
        return self.root

    def visit_Block(self, node: Block):
        super().generic_visit(node)

    def generic_visit(self, node: Any) -> Any:
        if isinstance(node, operation):
            self.current_block().add_op(node)
        elif isinstance(node, IrBlockAttr):  # 设置块属性
            self.current_block().attributes.update(node.attr)

    def visit_If(self, node: If):
        cb_last_out = self.exit_block()

        cb_body_in = self.enter_block(name="if_body")
        self.visit(node.blk_body)
        cb_body_out = self.exit_block()

        cb_else_in = self.enter_block(name="if_else")
        self.visit(node.blk_else)
        cb_else_out = self.exit_block()

        cb_last_out.cond = node.condition
        cb_last_out.true = cb_body_in
        cb_last_out.false = cb_else_in

        cb_next_in = self.enter_block(name="if_next")

        if not self.inline_catch and node.blk_body.excs.might:
            if not node.blk_body.excs.always:
                cb_body_out.cond = self.bf
                cb_body_out.false = cb_next_in
        else:
            cb_body_out.direct = cb_next_in

        if not self.inline_catch and  node.blk_else.excs.might:
            if not node.blk_else.excs.always:
                cb_else_out.cond = self.bf
                cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in

    def visit_For(self, node: For):
        cb_last_out = self.exit_block()

        cb_else_in = self.enter_block(name="for_else")
        self.visit(node.blk_else)
        cb_else_out = self.exit_block()

        cb_iter_in = self.enter_block(name="for_iter")
        self.push_exc_handler((RtStopIteration,), cb_else_in)
        self.visit(node.blk_iter)
        self.pop_exc_handler()
        cb_iter_out = self.exit_block()

        cb_next_in = self.enter_block(name="for_next")

        cb_body_in = self.enter_block(name="for_body")
        self.push_exc_handler((RtContinue,), cb_iter_in)
        self.push_exc_handler((RtBreak,), cb_next_in)
        # self.add_op(self.clear_flag_op()) #  进入 body 时清空 bf  TODO bf 的清理方式
        self.visit(node.blk_body)
        self.pop_exc_handler()
        self.pop_exc_handler()
        cb_body_out = self.exit_block()

        cb_catch_iter = BasicBlock(name="for_catch_iter")
        cb_catch_body = BasicBlock(name="for_catch_body")

        cb_iter = cb_catch_iter if not self.inline_catch and node.blk_iter.excs.might else cb_iter_in
        cb_body = cb_catch_body if not self.inline_catch and node.blk_body.excs.might else cb_body_in

        if not self.inline_catch and node.blk_iter.excs.might:
            cb_last_out.direct = cb_catch_iter
            cb_catch_iter.direct = cb_iter_in

            if node.blk_iter.excs.always:
                cb_catch_iter.direct = cb_else_in
            else:
                cb_catch_iter.cond = self.bf  # TODO iter 中是否需要允许抛出 RtStopIteration 以外的异常
                cb_catch_iter.false = cb_body
                cb_catch_iter.true = cb_else_in  # TODO 清理异常标志
        else:
            cb_last_out.direct = cb_iter_in
            cb_iter_out.direct = cb_body

        if not self.inline_catch and node.blk_body.excs.might:
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

        if not self.inline_catch and node.blk_else.excs.might:
            if not node.blk_else.excs.always:
                cb_else_out.cond = self.bf
                cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in


    def visit_While(self, node: While):
        cb_last_out = self.exit_block()

        cb_next_in = self.enter_block(name="while_next")

        cb_cond_in = self.enter_block(name="while_cond")
        self.visit(node.blk_cond)
        cb_cond_out = self.exit_block()

        cb_body_in = self.enter_block(name="while_body")
        self.push_exc_handler((RtContinue,), cb_body_in)
        self.push_exc_handler((RtBreak,), cb_next_in)
        self.visit(node.blk_body)
        self.pop_exc_handler()
        self.pop_exc_handler()
        cb_body_out = self.exit_block()

        cb_else_in = self.enter_block(name="while_else")
        self.visit(node.blk_else)
        cb_else_out = self.exit_block()

        if not self.inline_catch and node.blk_body.excs.might:
            cb_test = BasicBlock(name="while_test")
            cb_catch = BasicBlock(name="while_catch")
            cb_jump = MatchJump(self.bf, [
                JmpEq(RtContinue, cb_test),
                JmpEq(RtBreak, cb_next_in),
            ], inactive=0, name="while_jump")

            cb_test.cond = node.condition
            cb_test.true = cb_catch
            cb_test.false = cb_else_in

            cb_body_out.cond = self.bf
            cb_body_out.false = cb_cond_in

            # cb_next_in.add_op(self.clear_flag_op())  # TODO
            # cb_test.add_op(self.clear_flag_op())

            cb_catch.direct = cb_body_in
            cb_catch.cond = self.bf
            cb_catch.true = cb_jump

            cb_last_out.direct = cb_cond_in

            cb_cond_out.cond = self.bf
            cb_cond_out.false = cb_test
        else:
            cb_last_out.direct = cb_cond_in
            cb_cond_out.cond = node.condition
            cb_cond_out.true = cb_body_in
            cb_cond_out.false = cb_else_in

            cb_body_out.direct = cb_cond_in

        if not self.inline_catch and node.blk_else.excs.might:
            if not node.blk_else.excs.always:
                cb_else_out.cond = self.bf
                cb_else_out.false = cb_next_in
        else:
            cb_else_out.direct = cb_next_in


    def visit_Try(self, node: Try):
        cb_last_out = self.exit_block()

        cb_catch = BasicBlock(name="try_catch")

        cb_finally_in = self.enter_block(name="try_finally")
        self.visit(node.blk_finally)
        cb_finally_out = self.exit_block()

        # 优先于 body 构造 handler 块，使 InlinedRaise 能够识别对应的块
        cb_excepts = []
        for exc_handler in node.excepts:
            captures =set()
            for e in node.blk_try.excs.types:
                if e is not None and issubclass(e, exc_handler.eg):
                    captures.add(e)

            cb_exc_in = self.enter_block(name="try_except")
            # cb_exc_in.add_op(self.clear_flag_op())  # TODO
            self.visit(exc_handler.blk_handle)
            cb_exc_out = self.exit_block()
            cb_exc_out.direct = cb_finally_in
            cb_excepts.append((cb_exc_in, exc_handler.eg, captures))

        cb_else_in = self.enter_block(name="try_else")
        self.visit(node.blk_else)
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
        self.visit(node.blk_try)
        for _ in range(len(cb_excepts)):
            self.pop_exc_handler()
        cb_body_out = self.exit_block()

        self.pop_try_match()

        cb_next_in = self.enter_block(name="try_next")

        if not self.inline_catch and node.blk_try.excs.might:
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
            assert not node.blk_finally.excs.might, "启用 ir_inline_catch 时 finally 块不能存在呈递流程控制语句（continue, break, return 或抛出异常）"
            cb_finally_out.direct = cb_next_in
        else:
            if not node.blk_finally.excs.always:
                if node.blk_else.excs.might or node.blk_finally.excs.might or any(h.blk_handle.excs.might for h in node.excepts):
                    cb_finally_out.cond = self.bf
                    cb_finally_out.false = cb_next_in
                else:
                    # exception_handlers, else, finally 均不会抛出异常，则可以直接跳转
                    cb_finally_out.direct = cb_next_in

    def visit_Raise(self, node: Raise):
        # TODO err stack
        if not self.inline_catch:
            self.current_block().add_op(self.set_flag_op(node.exc))
        else:
            cb_last_out = self.exit_block()
            for eg, handler in self._exc_handler_in[::-1]:
                if isinstance(node.exc, eg):
                    cb_last_out.direct = handler
                    break
            else:
                cb_last_out.add_op(self.set_flag_op(node.exc))
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

    def visit_With(self, node: With):
        cb_last_out = self.exit_block()

        cb_enter_in = self.enter_block(name="with_enter")
        self.visit(node.blk_enter)
        cb_enter_out = self.exit_block()

        cb_body_in = self.enter_block(name="with_body")
        self.visit(node.blk_body)
        cb_body_out = self.exit_block()

        cb_exit_in = self.enter_block(name="with_exit")
        self.visit(node.blk_exit)
        cb_exit_out = self.exit_block()

        cb_next_in = self.enter_block(name="with_next")

        cb_last_out.direct = cb_enter_in

        if not self.inline_catch:

            if node.blk_body.excs.might:
                cb_catch = BasicBlock(name="with_catch")
                cb_catch.direct = cb_body_in
                cb_catch.cond = True
                cb_catch.true = cb_exit_in
            else:
                cb_catch = cb_body_in
                cb_body_out.direct = cb_exit_in

            if node.blk_enter.excs.might:
                cb_enter_out.cond = self.bf
                cb_enter_out.false = cb_catch
            else:
                cb_enter_out.direct = cb_catch

            if node.blk_exit.excs.might or node.blk_body.excs.might:
                cb_exit_out.cond = self.bf
                cb_exit_out.false = cb_next_in
            else:
                cb_exit_out.direct = cb_next_in
        else:
            cb_last_out.direct = cb_enter_in
            cb_enter_out.direct = cb_body_in
            cb_body_out.direct = cb_exit_in
            cb_exit_out.direct = cb_next_in

class CBSimplifier:

    def __init__(self, root: code_block):
        self.simplified = False
        self._blocks: list[code_block] = [root]
        self._ref_num = defaultdict(int)
        self._list_all()

    def _mark_simplified(self):
        self.simplified = True

    def _list_all(self):
        root = self._blocks[0]
        self._blocks.clear()

        def visit(node):
            if node is None or self._ref_num[node] > 1:
                return
            self._blocks.append(node)
            i = getattr(self, "iter_" + node.__class__.__name__, None)(node)
            try:
                node = next(i)
                while True:
                    self._ref_num[node] += 1
                    visit(node)
                    node = i.send(node)
            except StopIteration:
                pass

        visit(root)

    def _count_ref(self):
        self._ref_num.clear()
        for block in self._blocks:
            i = getattr(self, "iter_" + block.__class__.__name__, None)(block)
            try:
                node = next(i)
                while True:
                    if node is not None:
                        self._ref_num[node] += 1
                    node = i.send(node)
            except StopIteration:
                pass

    def simplify(self):
        mapping = {}
        for block in self._blocks:
            if block is not None:
                simplifier = getattr(self, "simplify_" + block.__class__.__name__)
                mapping[block] = simplifier(block)
        for block in self._blocks:
            i: Generator = getattr(self, "iter_" + block.__class__.__name__, None)(block)
            try:
                node = next(i)
                while True:
                    node = i.send(mapping[node] if node is not None else None)
            except StopIteration:
                pass
        return self._blocks[0]

    def iter_BasicBlock(self, node: BasicBlock):
        node.direct = yield node.direct
        node.true = yield node.true
        node.false = yield node.false

    def iter_MatchJump(self, node: MatchJump):
        for c in node.cases:
            c.target = yield c.target

    def simplify_BasicBlock(self, node: BasicBlock) -> code_block | None:
        return node

    def simplify_MatchJump(self, node: MatchJump) -> code_block | None:
        return node


class EmptyCBRemover(CBSimplifier):
    """
    消除空块和简化跳转逻辑
    """
    @staticmethod
    def is_empty(block: BasicBlock):
        return len(block.ops) == 0 and len(block.attributes) == 0

    def simplify_BasicBlock(self, cb: BasicBlock) -> code_block | None:
        if cb.true is cb.false and cb.direct is None:
            # 判断后跳转的目标为同一个，可以跳过判断
            cb.direct = cb.true
            cb.cond = None

        if cb.true is None and cb.false is None:
            cb.cond = None
            self._mark_simplified()
        elif cb.cond is None:
            cb.true = cb.false = None
            self._mark_simplified()

        if cb.cond is None and isinstance(cb.direct, BasicBlock) and self.is_empty(cb.direct):
            # 当前块直接跳转空块且无条件跳转，将空块的跳转方式提前
            cb.cond = cb.direct.cond
            cb.false = cb.direct.false
            cb.true = cb.direct.true
            cb.direct = cb.direct.direct
            self._mark_simplified()
        if self.is_empty(cb) and cb.cond is None:
            # 不应存在全空的环路
            self._mark_simplified()
            return cb.direct
        if cb.cond is not None:
            # 跳过相同条件的空块
            if isinstance(cb.true, BasicBlock) and cb.true.cond is cb.cond and self.is_empty(cb.true) and cb.true.direct is None:
                cb.true = cb.true.true
                self._mark_simplified()
            if isinstance(cb.false, BasicBlock) and cb.false.cond is cb.cond and self.is_empty(cb.false) and cb.false.direct is None:
                cb.false = cb.false.false
                self._mark_simplified()
        return cb

    def simplify_MatchJump(self, cb: MatchJump) -> code_block | None:
        if len(cb.cases) == 0:
            self._mark_simplified()
            return None
        # 无跳转目标的case暂时不能删除，可能存在flag清除的作用
        return cb


class CBInliner(CBSimplifier):

    def __init__(self, root: code_block, inline_thresh: int):
        super().__init__(root)
        self.inline_thresh = inline_thresh

    def simplify(self):
        self._count_ref()
        return super().simplify()

    def simplify_BasicBlock(self, cb: BasicBlock) -> code_block | None:
        if cb.cond is None and isinstance(cb.direct, BasicBlock) and len(cb.direct.attributes) == 0:
            if (self.inline_thresh >= 0 and self._ref_num[cb.direct] == 1) or len(cb.direct.ops) <= self.inline_thresh:
                # cb.direct 不会是 cb
                cb.cond = cb.direct.cond
                cb.false = cb.direct.false
                cb.true = cb.direct.true
                cb.ops.extend(cb.direct.ops)
                cb.direct = cb.direct.direct
                self._mark_simplified()
        return cb


class Compiler:

    def __init__(self, config: IrCfg):
        self.config = config

    def compile(self, ctx: Scope) -> list[code_block]:
        cb = Expander(ctx._root_block, self.config.ir_bf, self.config, ctx.name).expand()

        for _ in range(self.config.ir_simplify):
            simplifier = EmptyCBRemover(cb)
            cb = simplifier.simplify()
            if cb is None:
                return []
            if not simplifier.simplified:
                break

        for _ in range(self.config.ir_simplify):
            inliner = CBInliner(cb, self.config.ir_inline_thresh)
            cb = inliner.simplify()
            if not inliner.simplified:
                break

        collector = CBSimplifier(cb)
        return collector._blocks