import importlib.resources
from typing import Any

from dominate.tags import *
from dominate.util import raw

from pymcf.ast_ import NodeVisitor, Scope, operation, compiler_hint, If, Context, Raise, AST, \
    For, While, Try, Inplace, Call
from .reprs import repr_operation, repr_compiler_hint


class _CtxDumper(NodeVisitor):

    def dump(self, ctx: Context) -> str:
        with html() as doc:
            with head():
                style(raw(importlib.resources.read_text(__name__, 'ast.css')))
            with body():
                with table(cls="root"):
                    with tr(), td():
                        div(ctx.name, title="\n".join(repr(e) for e in ctx.excs.types), cls="head_root")
                    with tr(), td():
                        self.visit(ctx.root_scope)
        return str(doc)

    def visit(self, node: AST):
        if isinstance(node, operation):
            with div(cls="operation"):
                b(node.__class__.__name__)
                span(repr_operation(node))
        elif isinstance(node, compiler_hint):
            with div(cls="compiler_hint"):
                b(node.__class__.__name__)
                span(repr_compiler_hint(node))
        else:
            super().visit(node)

    def visit_Scope(self, node: Scope):
        with table(cls="scope"):
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
                with tr(cls="scope_line"):
                    with td():
                        div(f"0.", cls="exc_never")
                    with td():
                        div(cls="pass")

    def visit_Raise(self, node: Raise):
        div(repr(node.exc), cls="raise")

    def visit_If(self, node: If):
        with table():
            with tr(), td():
                div(repr(node.condition), cls="if_cond cf")
            with tr(), td():
                self.visit(node.sc_body)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.sc_else)

    def visit_For(self, node: For):
        with table():
            with tr(), td():
                div(repr(node.iterator), cls="for_iter cf")
            with tr(), td():
                self.visit(node.sc_body)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.sc_else)

    def visit_While(self, node: While):
        with table():
            with tr(), td():
                div(repr(node.condition), cls="while_cond cf")
            with tr(), td():
                self.visit(node.sc_body)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.sc_else)

    def visit_Try(self, node: Try):
        with table():
            with tr(), td():
                div(cls="try cf")
            with tr(), td():
                self.visit(node.sc_try)
            for handler in node.excepts:
                with tr(), td():
                    div(repr(handler.eg), cls="except cf")
                with tr(), td():
                    self.visit(handler.sc_handle)
            with tr(), td():
                div(cls="else cf")
            with tr(), td():
                self.visit(node.sc_else)
            with tr(), td():
                div(cls="finally cf")
            with tr(), td():
                self.visit(node.sc_finally)

    def visit_Call(self, node: Call):
        div(repr(node.func), cls="call")


def dump_context(ctx: Context) -> str:
    return _CtxDumper().dump(ctx)