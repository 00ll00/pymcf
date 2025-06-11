from html import escape as html_escape

from graphviz import escape as gv_escape
from pymcf.mc.commands import NameRef, UUIDRef

from pymcf.data import Score, Entity

from pymcf.ast_ import *
from pymcf.ir.codeblock import jmpop, JmpEq, JmpNotEq


def escape(s):
    return gv_escape(html_escape(str(s)))


def repr_value(value):
    if isinstance(value, Score):
        target = value.target
        objective = value.objective
        if isinstance(target.__metadata__, NameRef):
            return f"Score({target.__metadata__.name!r}, {objective.__metadata__.objective!r})"
        if isinstance(target.__metadata__, UUIDRef):
            return f"Score({target.__metadata__.uuid!r}, {objective.__metadata__.objective!r})"
    if isinstance(value, FormattedData):
        return repr_value(value.data)
    if isinstance(value, Entity):
        if isinstance(value.__metadata__, UUIDRef):
            return str(value.__metadata__.uuid)
    return repr(value)


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
        case Not():
            return "not"
        case _:
            raise NotImplementedError


def repr_operation(op: operation) -> str:
    match op:
        case Raw():
            return ' '.join(part if isinstance(part, str) else f"${repr_value(part)}" for part in op.code)
        case Assign():
            return f"{repr_value(op.target)} = {repr_value(op.value)}"
        case UnaryOp():
            return f"{repr_value(op.target)} = {repr_operator(op.op)} {repr_value(op.value)}"
        case Inplace():
            return f"{repr_value(op.target)} = {repr_value(op.target)} {repr_operator(op.op)} {repr_value(op.value)}"
        case Compare():
            return f"{repr_value(op.target)} = {repr_value(op.left)} {repr_operator(op.op)} {repr_value(op.right)}"
        case _:
            raise NotImplementedError


def repr_jmpop(op: jmpop) -> str:
    match op:
        case JmpEq():
            return f"$ == {repr_value(op.value)}"
        case JmpNotEq():
            return f"$ != {repr_value(op.value)}"
        case _:
            raise NotImplementedError


def repr_compiler_hint(h: compiler_hint) -> str:
    return ", ".join(f"{attr}={getattr(h, attr, None)!r}" for attr in h._attributes)