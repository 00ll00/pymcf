from _ast import UAdd, USub, Not, Invert, And, Or, Add, Sub, Mult, Div, FloorDiv, Mod, Pow, LShift
from numbers import Real
from typing import SupportsInt

from ..ast_ import operation, Raw, Assign, UnaryOp, Inplace, Compare, LtE, Gt, GtE, Eq, NotEq, Lt, Context
from ..ir import BasicBlock
from ..data import Score, Nbt
from .commands import Command, RawCommand, ScoreRef, OpAssign, NbtPath, Execute, ExecuteChain, GetValue, DataGet, \
    SetConst, DataModifyFrom, OpSub, ScoreRange, OpMul, OpAdd, OpDiv, OpMod


def translate(op: operation) -> Command | list[Command]:
    if isinstance(op, Raw):
        return RawCommand(op.code)


    elif isinstance(op, Assign):
        target = op.target
        value = op.value
        if isinstance(target, Score):
            if isinstance(value, Score):
                return OpAssign(target.__metadata__, value.__metadata__)
            elif isinstance(value, Nbt):
                chain = ExecuteChain()
                chain.store('result').score(target.__metadata__).run(DataGet(value.__metadata__.target, value.__metadata__.path))
                return Execute(chain)
            elif isinstance(value, Real):
                return SetConst(target.__metadata__, int(value))
            else:
                raise NotImplementedError
        elif isinstance(target, Nbt):
            raise NotImplementedError
        else:
            raise NotImplementedError


    elif isinstance(op, UnaryOp):
        target = op.target
        value = op.value
        if isinstance(target, Score):
            if isinstance(value, Score):
                match op.op:
                    case UAdd():
                        return OpAssign(target.__metadata__, value.__metadata__)
                    case USub():
                        return [
                            SetConst(target.__metadata__, 0),
                            OpSub(target.__metadata__, value.__metadata__)
                        ]
                    case Not():
                        chain = ExecuteChain()
                        chain.store('success').score(target.__metadata__).cond('if').score_range(value.__metadata__, ScoreRange(0, 0))
                        return Execute(chain)
                    case Invert():
                        raise NotImplementedError
            raise NotImplementedError
        else:
            raise NotImplementedError


    elif isinstance(op, Inplace):
        target = op.target
        value = op.value
        assert isinstance(target, Score), "not implemented"
        if isinstance(value, Score):
            match op.op:
                case And():
                    return OpMul(target.__metadata__, value.__metadata__)
                case Or():
                    chain = ExecuteChain()
                    chain.cond('if').score_range(target.__metadata__, ScoreRange(0, 0)).run(OpAssign(target.__metadata__, value.__metadata__))
                    return Execute(chain)
                case Add():
                    return OpAdd(target.__metadata__, value.__metadata__)
                case Sub():
                    return OpSub(target.__metadata__, value.__metadata__)
                case Mult():
                    return OpMul(target.__metadata__, value.__metadata__)
                case Div():
                    return OpDiv(target.__metadata__, value.__metadata__)
                case FloorDiv():
                    return OpDiv(target.__metadata__, value.__metadata__)
                case Mod():
                    return OpMod(target.__metadata__, value.__metadata__)


    elif isinstance(op, Compare):
        target = op.target
        left = op.left
        right = op.right
        cmp = op.op
        assert isinstance(target, Score), "not implemented"
        if not isinstance(left, Score):
            left, right = right, left
            cmp = cmp.opposite()
        assert isinstance(left, Score), "not implemented"
        if isinstance(right, Score):
            match cmp:
                case Eq():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score(left.__metadata__, '=', right.__metadata__)
                    return Execute(chain)
                case NotEq():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('unless').score(left.__metadata__, '=', right.__metadata__)
                    return Execute(chain)
                case Lt():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score(left.__metadata__, '<', right.__metadata__)
                    return Execute(chain)
                case LtE():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score(left.__metadata__, '<=', right.__metadata__)
                    return Execute(chain)
                case Gt():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score(left.__metadata__, '>', right.__metadata__)
                    return Execute(chain)
                case GtE():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score(left.__metadata__, '>=', right.__metadata__)
                    return Execute(chain)
                case _:
                    raise NotImplementedError
        elif isinstance(right, SupportsInt):
            right = int(right)
            match cmp:
                case Eq():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score_range(left.__metadata__, ScoreRange(right, right))
                    return Execute(chain)
                case NotEq():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('unless').score_range(left.__metadata__, ScoreRange(right, right))
                    return Execute(chain)
                case Lt():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score_range(left.__metadata__, ScoreRange(None, right - 1))
                    return Execute(chain)
                case LtE():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score_range(left.__metadata__, ScoreRange(None, right))
                    return Execute(chain)
                case Gt():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score_range(left.__metadata__, ScoreRange(right + 1, None))
                    return Execute(chain)
                case GtE():
                    chain = ExecuteChain()
                    chain.store('success').score(target.__metadata__).cond('if').score_range(left.__metadata__, ScoreRange(right, None))
                    return Execute(chain)
                case _:
                    raise NotImplementedError


    raise NotImplementedError


def gen(cb: BasicBlock, ctx: Context):
    cmds = []
    for op in cb.ops:
        if isinstance(op, operation):
            cmd = translate(op).resolve(ctx)
            if isinstance(cmd, list):
                cmds.extend(cmd)
            else:
                cmds.append(cmd)
    return cmds
