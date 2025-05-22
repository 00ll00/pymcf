from _ast import UAdd, USub, Not, Invert, And, Or
from numbers import Real

from ..ast_ import operation, Raw, Assign, UnaryOp, BoolOp, AugAssign
from ..ir import BasicBlock
from ..data import Score, Nbt
from .commands import Command, RawCommand, ScoreRef, OpAssign, NbtPath, Execute, ExecuteChain, GetValue, DataGet, \
    SetConst, DataModifyFrom, OpSub, ScoreRange


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
        else:
            raise NotImplementedError


    elif isinstance(op, AugAssign):
        ...


def gen(cb: BasicBlock):
    cmds = []
    for op in cb.ops:
        if isinstance(op, operation):
            cmd = translate(op)
            if isinstance(cmd, list):
                cmds.extend(cmd)
            else:
                cmds.append(cmd)
