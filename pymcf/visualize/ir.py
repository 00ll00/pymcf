import ast

import graphviz as gv

from pymcf.ast_ import operation, control_flow, Call, Inplace, UnaryOp, Compare
from pymcf.ir import BasicBlock, MatchJump
from pymcf.ir.codeblock import jmpop
from pymcf.visualize.reprs import repr_operation, repr_jmpop, escape


class _GraphVizDumper(ast.NodeVisitor):

    def __init__(self, root: BasicBlock):
        self.visited = set()
        self.root = root
        self.graph = gv.Digraph()
        self.graph.attr(
            splines="ortho",
            bgcolor="white",
        )
        self.graph.node_attr = {
            "fontname": "Courier New",
        }
        self.graph.edge_attr = {
            "fontname": "Courier New",
        }
        if root is not None:
            self.visit(root)

    def visit(self, node):
        if node in self.visited:
            return
        self.visited.add(node)
        super().visit(node)

    @staticmethod
    def node_name(node):
        return f"node_{id(node)}"

    @staticmethod
    def repr_node(op):
        if isinstance(op, operation):
            r = repr_operation(op)
        elif isinstance(op, jmpop):
            r = repr_jmpop(op)
        elif isinstance(op, Call):
            r = f"{op.func!r}()"
        class_name = op.__class__.__name__
        if isinstance(op, Inplace | UnaryOp | Compare):
            class_name += f'.{op.op.__class__.__name__}'
        return f"""<td align="left"><b>{escape(class_name)}</b>  </td><td align="left">{escape(r)}</td>"""

    def visit_BasicBlock(self, node: BasicBlock):
        self.generic_visit(node)
        begin = node is self.root
        end = node.direct is None and node.true is None and node.false is None
        self.graph.node(
            name=self.node_name(node),
            label=f"""<
                    <table border="0" cellborder="1" cellspacing="0" cellpadding="4">
                        <tr><td{' bgcolor="#ccffff"' if begin else ''}><b>{escape(node.name)}</b></td></tr>
                        <tr><td bgcolor="gray95">{f"""<table border="0" cellborder="0" cellspacing="2" cellpadding="0">
                            {'\n'.join(f'<tr><td align="right">{i + 1}.</td>{self.repr_node(op)}</tr>' for i, op in enumerate(node.ops))}
                        </table>""" if node.ops else ""}</td></tr>
                        <tr><td{' bgcolor="#ffffcc"' if end else ''}>{escape(node.cond)}</td></tr>
                    </table>
                    >""",
            shape="plain",
            style="filled",
            fillcolor="gray90",
        )
        if node.direct is not None:
            self.graph.edge(
                tail_name=self.node_name(node) + ":s",
                head_name=self.node_name(node.direct) + ":n",
                color="blue",
            )
        if node.cond is not None:
            if node.true is not None:
                self.graph.edge(
                    tail_name=self.node_name(node) + ":sw",
                    head_name=self.node_name(node.true) + ":n",
                    color="green",
                )
            if node.false is not None:
                self.graph.edge(
                    tail_name=self.node_name(node) + ":se",
                    head_name=self.node_name(node.false) + ":n",
                    color="red",
                )

    def visit_MatchJump(self, node: MatchJump):
        self.generic_visit(node)
        self.graph.node(
            name=self.node_name(node),
            label=f"""<
            <table border="0" cellborder="1" cellspacing="0" cellpadding="4">
                <tr><td><b>{escape(node.name)}</b>  [inactivate={escape(node.inactive)}]</td></tr>
                <tr><td bgcolor="#ffeeff">{f"""<table border="0" cellborder="0" cellspacing="0" >
                    {'\n'.join(f'<tr><td align="left">[{i+1}]</td>{self.repr_node(case)}</tr>' for i, case in enumerate(node.cases))}
                </table>""" if node.cases else ""}</td></tr>
                <tr><td>{escape(node.flag)}</td></tr>
            </table>
            >""",
            shape="plain",
            style="filled",
            fillcolor="#ffddff",
        )

        for i, case in enumerate(node.cases):
            if case.target is None:
                continue
            self.graph.edge(
                tail_name=self.node_name(node) +f":s",
                head_name=self.node_name(case.target) + ":n",
                color="magenta",
                label=f"[{i+1}]",
                fontcolor="magenta",
                decorate="true",
            )


def draw_ir(root: BasicBlock) -> gv.Digraph:
    return _GraphVizDumper(root).graph