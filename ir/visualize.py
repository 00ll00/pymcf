import ast
import json.encoder
from html import escape as html_escape

import graphviz as gv
from graphviz import escape as gv_escape

from ir.codeblock import code_block, BasicBlock, MatchJump


def escape(s):
    return gv_escape(html_escape(str(s)))

def json_escape(s):
    return json.dumps(str(s))

class GraphVizDumper(ast.NodeVisitor):

    def __init__(self, root: code_block):
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
        return f"<b>{escape(op.__class__.__name__)}</b>: {escape(', '.join(f'{attr}={getattr(op, attr)!r}' for attr in op._fields))}"

    def visit_BasicBlock(self, node: BasicBlock):
        self.generic_visit(node)
        begin = node is self.root
        end = node.direct is None and node.true is None and node.false is None
        self.graph.node(
            name=self.node_name(node),
            label=f"""<
                    <table border="0" cellborder="1" cellspacing="0" cellpadding="4">
                        <tr><td{' bgcolor="#ccffff"' if begin else ''}><b>{escape(node.name)}</b></td></tr>
                        <tr><td bgcolor="gray95">{f"""<table border="0" cellborder="0" cellspacing="0" >
                            {'\n'.join(f'<tr><td align="left">{i + 1}. {self.repr_node(op)}</td></tr>' for i, op in enumerate(node.ops))}
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
                <tr><td><b>{escape(node.name)}</b> [inactivate={escape(node.inactive)}]</td></tr>
                <tr><td bgcolor="#ffeeff">{f"""<table border="0" cellborder="0" cellspacing="0" >
                    {'\n'.join(f'<tr><td align="left">{f"[{i+1}] <b>{escape(case.__class__.__name__)}</b>: {escape(', '.join(f'{attr}={(getattr(case, attr))!r}' for attr in case._fields if attr != "target"))}"}</td></tr>' for i, case in enumerate(node.cases))}
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
