from html import escape as html_escape

from graphviz import escape as gv_escape

from pymcf.ast_ import *
from pymcf.ir.codeblock import jmpop, JmpEq, JmpNotEq


def escape(s):
    return gv_escape(html_escape(str(s)))


def repr_unaryop(op: unaryop) -> str:
    match op:
        case UAdd():
            return "+"
        case USub():
            return "-"
        case Not():
            return "not "
        case Invert():
            return "~"
        case _:
            raise NotImplementedError


def repr_operator(op: operator | boolop | cmpop) -> str:
    match op:
        case And():
            return "and"
        case Or():
            return "or"
        case Add():
            return "+"
        case Sub():
            return "-"
        case Mult():
            return "*"
        case Div():
            return "/"
        case FloorDiv():
            return "//"
        case Mod():
            return "%"
        case Pow():
            return "**"
        case LShift():
            return "<<"
        case RShift():
            return ">>"
        case BitOr():
            return "|"
        case BitXor():
            return "^"
        case BitAnd():
            return "&"
        case MatMult():
            return "@"
        case Eq():
            return "=="
        case NotEq():
            return "!="
        case Lt():
            return "<"
        case LtE():
            return "<="
        case Gt():
            return ">"
        case GtE():
            return ">="
        case Is():
            return "is"
        case IsNot():
            return "is not"
        case In():
            return "in"
        case NotIn():
            return "not in"
        case _:
            raise NotImplementedError


def repr_operation(op: operation) -> str:
    match op:
        case Raw():
            return repr(op.code)
        case Assign():
            return f"{op.target!r} = {op.value!r}"
        case UnaryOp():
            return f"{op.target!r} = {repr_operator(op.op)}{op.value!r}"
        case Inplace():
            return f"{op.target!r} = {op.target!r} {repr_operator(op.op)} {op.value!r}"
        case Compare():
            return f"{op.target!r} = {op.left!r} {repr_operator(op.op)} {op.right!r}"
        case _:
            raise NotImplementedError


def repr_jmpop(op: jmpop) -> str:
    match op:
        case JmpEq():
            return f"$ == {op.value!r}"
        case JmpNotEq():
            return f"$ != {op.value!r}"
        case _:
            raise NotImplementedError


def repr_compiler_hint(h: compiler_hint) -> str:
    return ", ".join(f"{attr}={getattr(h, attr, None)!r}" for attr in h._attributes)