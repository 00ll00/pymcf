import importlib.resources
from typing import Any

from dominate.tags import *
from dominate.util import raw
from pymcf.visualize.reprs import repr_value

from pymcf.ast_ import NodeVisitor, Block, operation, compiler_hint, If, Scope, Raise, AST, \
    For, While, Try, Inplace, Call, With, UnaryOp, Compare
from .reprs import repr_operation, repr_compiler_hint


class _ScopeDumper(NodeVisitor):

    def dump(self, scope: Scope) -> str:
        with html() as doc:
            with head():
                style(raw(importlib.resources.read_text(__name__, 'ast.css')))
            with body():
                with table(cls="root"):
                    with tr(), td():
                        div(scope.name, title="\n".join(repr(e) for e in scope.excs.types), cls="head_root")
                    with tr(), td():
                        self.visit(scope._root_block)
        return str(doc)

    def visit(self, node: AST):
        if isinstance(node, operation):
            with div(cls="operation"):
                name = node.__class__.__name__
                if isinstance(node, Inplace | UnaryOp | Compare):
                    name += f'.{node.op.__class__.__name__}'
                b(name)
                span(repr_operation(node))
        elif isinstance(node, compiler_hint):
            with div(cls="compiler_hint"):
                b(node.__class__.__name__)
                span(repr_compiler_hint(node))
        else:
            super().visit(node)

    def visit_Block(self, node: Block):
        with table(cls="block"):
            with colgroup():
                col(width=str((len(str(len(node.flow)+1))+1) * 10) + "px")
            if node.flow:
                for i, op in enumerate(node.flow):
                    with tr():
                        with td():
                            div(f"{i+1}.", title="\n".join(repr(e) for e in op.excs.types), cls=("exc_always" if op.excs.always else "exc_might" if op.excs.might else "exc_never") + " lineno")
                        with td():
                            self.visit(op)
            else:
                with tr(cls="block_line"):
                    with td():
                        div(f"0.", cls="exc_never")
                    with td():
                        div(cls="pass")

    def visit_Raise(self, node: Raise):
        div(repr(node.exc), cls="raise")

    def visit_If(self, node: If):
        with table():
            with tr(), td():
                div(repr_value(node.condition), cls="if_cond cf")
            with tr(), td():
                self.visit(node.blk_body)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.blk_else)

    def visit_For(self, node: For):
        with table():
            with tr(), td():
                div(repr_value(node.iterator), cls="for_iter cf")
            with tr(), td():
                self.visit(node.blk_body)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.blk_else)

    def visit_While(self, node: While):
        with table():
            with tr(), td():
                div(repr_value(node.condition), cls="while_cond cf")
            with tr(), td():
                self.visit(node.blk_body)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.blk_else)

    def visit_Try(self, node: Try):
        with table():
            with tr(), td():
                div(cls="try cf")
            with tr(), td():
                self.visit(node.blk_try)
            for handler in node.excepts:
                with tr(), td():
                    div(repr_value(handler.eg), cls="except cf")
                with tr(), td():
                    self.visit(handler.blk_handle)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.blk_else)
            with tr(), td():
                div(cls="finally cf")
            with tr(), td():
                self.visit(node.blk_finally)

    def visit_Call(self, node: Call):
        div(repr_value(node.func), cls="call")

    def visit_With(self, node: With):
        with table():
            with tr(), td():
                div(repr_value(node.ctx), cls="with cf")
            with tr(), td():
                self.visit(node.blk_body)


def dump_context(scope: Scope) -> str:
    return _ScopeDumper().dump(scope)