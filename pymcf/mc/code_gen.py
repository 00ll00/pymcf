from typing import SupportsInt

from .commands import Command, RawCommand, OpAssign, Execute, ExecuteChain, DataGet, \
    SetConst, OpSub, ScoreRange, OpMul, OpAdd, OpDiv, OpMod, AddConst, RemConst, Function, NSName
from .environment import Env
from ..ast_ import operation, Raw, Assign, UnaryOp, Inplace, Compare, LtE, Gt, GtE, Eq, NotEq, Lt, UAdd, USub, Not, \
    Invert, And, Or, Add, Sub, Mult, Div, FloorDiv, Mod
from ..data import Score, Nbt
from ..ir import BasicBlock, MatchJump, code_block
from ..ir.codeblock import JmpEq


class MCF:

    def __init__(self, name: str, cmds: list[Command], env: Env):
        self.name = name
        self.cmds = cmds
        self.env = env

    def gen_code(self) -> str:
        return '\n'.join(cmd.resolve(self.env) for cmd in self.cmds)



class Translator:

    def __init__(self, env: Env):
        self.env = env


    def translate_op(self, op: operation) -> Command | list[Command]:
        if isinstance(op, Raw):
            return RawCommand(op.code)


        elif isinstance(op, Assign):
            target = op.target
            value = op.value
            if isinstance(target, Score):
                if isinstance(value, Score):
                    return OpAssign(target.__metadata__, value.__metadata__)
                elif isinstance(value, Nbt):
                    return (ExecuteChain().store('result').score(target.__metadata__)
                                   .run(DataGet(value.__metadata__.target, value.__metadata__.path)))
                elif isinstance(value, SupportsInt):
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
                            return (ExecuteChain().store('success').score(target.__metadata__)
                                           .cond('if').score_range(value.__metadata__, ScoreRange(0, 0)).finish())
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
                        return (ExecuteChain().cond('if').score_range(target.__metadata__, ScoreRange(0, 0))
                                       .run(OpAssign(target.__metadata__, value.__metadata__)))
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
                    case _:
                        raise NotImplementedError
            elif isinstance(value, SupportsInt):
                value = int(value)
                match op.op:
                    case And():
                        if value:
                            return []
                        else:
                            return SetConst(target.__metadata__, 0)
                    case Or():
                        if value:
                            return SetConst(target.__metadata__, 1)
                        else:
                            return []
                    case Add():
                        return AddConst(target.__metadata__, value)
                    case Sub():
                        return RemConst(target.__metadata__, value)
                    case Mult():
                        return OpMul(target.__metadata__, self.env.get_const_score(value))
                    case Div():
                        return OpDiv(target.__metadata__, self.env.get_const_score(value))
                    case FloorDiv():
                        return OpDiv(target.__metadata__, self.env.get_const_score(value))
                    case Mod():
                        return OpMod(target.__metadata__, self.env.get_const_score(value))
                    case _:
                        raise NotImplementedError


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
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score(left.__metadata__, '=', right.__metadata__).finish())
                    case NotEq():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('unless').score(left.__metadata__, '=', right.__metadata__).finish())
                    case Lt():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score(left.__metadata__, '<', right.__metadata__).finish())
                    case LtE():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score(left.__metadata__, '<=', right.__metadata__).finish())
                    case Gt():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score(left.__metadata__, '>', right.__metadata__).finish())
                    case GtE():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score(left.__metadata__, '>=', right.__metadata__).finish())
                    case _:
                        raise NotImplementedError
            elif isinstance(right, SupportsInt):
                right = int(right)
                match cmp:
                    case Eq():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score_range(left.__metadata__, ScoreRange(right, right)).finish())
                    case NotEq():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('unless').score_range(left.__metadata__, ScoreRange(right, right)).finish())
                    case Lt():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score_range(left.__metadata__, ScoreRange(None, right - 1)).finish())
                    case LtE():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score_range(left.__metadata__, ScoreRange(None, right)).finish())
                    case Gt():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score_range(left.__metadata__, ScoreRange(right + 1, None)).finish())
                    case GtE():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                       .cond('if').score_range(left.__metadata__, ScoreRange(right, None)).finish())
                    case _:
                        raise NotImplementedError


        raise NotImplementedError

    def gen_BasicBlcok(self, cb: BasicBlock) -> MCF:
        path = self.env.function_name(cb)
        cmds = []
        for op in cb.ops:
            if isinstance(op, operation):
                cmd = self.translate_op(op)
                if isinstance(cmd, list):
                    cmds.extend(cmd)
                else:
                    cmds.append(cmd)
        if cb.direct is not None:
            cmds.append(Function(cb.direct))
        if cb.cond is not None:
            assert isinstance(cb.cond, Score)
            cmds.append(ExecuteChain().cond('if').score_range(cb.cond.__metadata__, ScoreRange(0, 0))
                                .run(Function(cb.false)))
            cmds.append(ExecuteChain().cond('unless').score_range(cb.cond.__metadata__, ScoreRange(0, 0))
                                .run(Function(cb.true)))
        return MCF(path, cmds, self.env)

    def gen_MachJump(self, cb: MatchJump):
        raise NotImplementedError

    def translate(self, cb: code_block) -> MCF:
        if isinstance(cb, BasicBlock):
            return self.gen_BasicBlcok(cb)
        elif isinstance(cb, MatchJump):
            return self.gen_MachJump(cb)
        else:
            raise NotImplementedError