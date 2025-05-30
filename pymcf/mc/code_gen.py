import math
from functools import reduce
from typing import SupportsInt, Self

from .commands import Command, RawCommand, OpAssign, Execute, ExecuteChain, DataGet, \
    SetConst, OpSub, NumRange, OpMul, OpAdd, OpDiv, OpMod, AddConst, RemConst, Function, NSName, ReturnRun, GetValue, \
    ResetValue, AtS
from .scope import MCFScope
from ..ast_ import operation, Raw, Assign, UnaryOp, Inplace, Compare, LtE, Gt, GtE, Eq, NotEq, Lt, UAdd, USub, Not, \
    Invert, And, Or, Add, Sub, Mult, Div, FloorDiv, Mod, RtBaseExc, Call
from ..ast_.runtime import _RtBaseExcMeta
from ..data import Score, Nbt
from ..ir import BasicBlock, MatchJump, code_block
from ..ir.codeblock import JmpEq, JmpNotEq


class MultiRange:

    EMPTY: Self

    def __init__(self, vmin: int = -math.inf, vmax: int = math.inf, *, _valid: list[int] = None):
        if _valid is None:
            assert vmin <= vmax
            self.valid = [vmin, vmax]
        else:
            _valid = list(_valid)
            assert len(_valid) % 2 == 0
            if len(_valid) > 2:
                for i in range(len(_valid) - 2)[:0:-2]:
                    if _valid[i] + 1 >= _valid[i + 1]:
                        _valid.pop(i + 1)
                        _valid.pop(i)
            self.valid = _valid

    def __invert__(self):
        valid = []
        if self.valid[0] != - math.inf:
            valid.extend((-math.inf, self.valid[0] - 1))
        for l, h in zip(self.valid[1::2], self.valid[2::2]):
            valid.extend((l + 1, h - 1))
        if self.valid[-1] != math.inf:
            valid.extend((self.valid[-1] + 1, math.inf))
        return MultiRange(_valid=valid)

    def __or__(self, other: Self):
        li = len(self.valid)
        lj = len(other.valid)
        if li == 0:
            return MultiRange(_valid=other.valid)
        if lj == 0:
            return MultiRange(_valid=self.valid)
        valid = []
        i = j = 0
        if self.valid[i] < other.valid[j]:
            last = self.valid[i: i + 2]
            i += 2
        else:
            last = other.valid[j: j + 2]
            j += 2
        while True:
            if i >= li and j >= lj:
                valid.extend(last)
                return MultiRange(_valid=valid)
            if j >= lj or i < li and self.valid[i] < other.valid[j]:
                curr = self.valid[i: i + 2]
                i += 2
            else:
                curr = other.valid[j: j + 2]
                j += 2

            if curr[0] > last[1]:
                valid.extend(last)
                last = curr
            else:
                last = min(curr[0], last[0]), max(curr[1], last[1])

    def __and__(self, other: Self):
        return ~(~self | ~other)

    def valid_ranges(self) -> list[tuple[int, int]]:
        valid = list(None if v in {math.inf, -math.inf} else v for v in self.valid)
        return list(zip(valid[0::2], valid[1::2]))


MultiRange.EMPTY = MultiRange(_valid=[])


class MCF:

    def __init__(self, name: str, cmds: list[Command], scope: MCFScope):
        self.name = name
        self.nsname = scope.name + ":" + self.name
        self.cmds = cmds
        self.scope = scope

    def gen_code(self) -> str:
        return '\n'.join(cmd.resolve(self.scope) for cmd in self.cmds)


class Translator:

    def __init__(self, scope: MCFScope):
        self.scope = scope

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
                elif value is None:
                    return ResetValue(target.__metadata__)
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
                                    .cond('if').score_range(value.__metadata__, NumRange(0, 0)).finish())
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
                        return (ExecuteChain().cond('if').score_range(target.__metadata__, NumRange(0, 0))
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
                        return OpMul(target.__metadata__, self.scope.get_const_score(value).__metadata__)
                    case Div():
                        return OpDiv(target.__metadata__, self.scope.get_const_score(value).__metadata__)
                    case FloorDiv():
                        return OpDiv(target.__metadata__, self.scope.get_const_score(value).__metadata__)
                    case Mod():
                        return OpMod(target.__metadata__, self.scope.get_const_score(value).__metadata__)
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
                                .cond('if').score_range(left.__metadata__, NumRange(right, right)).finish())
                    case NotEq():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                .cond('unless').score_range(left.__metadata__, NumRange(right, right)).finish())
                    case Lt():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                .cond('if').score_range(left.__metadata__, NumRange(None, right - 1)).finish())
                    case LtE():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                .cond('if').score_range(left.__metadata__, NumRange(None, right)).finish())
                    case Gt():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                .cond('if').score_range(left.__metadata__, NumRange(right + 1, None)).finish())
                    case GtE():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                .cond('if').score_range(left.__metadata__, NumRange(right, None)).finish())
                    case _:
                        raise NotImplementedError
            elif right is None:
                # == None 用于判断 score 是否存在
                match cmp:
                    case Eq():
                        return (ExecuteChain().store('success').score(target.__metadata__)
                                .run(GetValue(left.__metadata__)))
                    case NotEq():
                        raise NotImplementedError
                    case _:
                        raise ValueError("None 不能用于比较大小")
            else:
                raise NotImplementedError

        elif isinstance(op, Call):
            # call 涉及上下文切换
            scope = op.func
            assert isinstance(scope, MCFScope)
            if scope.executor is None or scope.executor == self.scope.executor:
                return Function(op.func)
            else:
                return ExecuteChain().as_entity(scope.executor.__metadata__).at_entity_pos(AtS()).rotated_as_entity(AtS()).run(Function(op.func))


        raise NotImplementedError

    def gen_BasicBlcok(self, cb: BasicBlock) -> MCF:
        path = self.scope.sub_name(cb)
        cmds = []
        for op in cb.ops:
            if isinstance(op, operation | Call):
                cmd = self.translate_op(op)
                if isinstance(cmd, list):
                    cmds.extend(cmd)
                else:
                    cmds.append(cmd)
        if cb.direct is not None:
            cmds.append(Function(cb.direct))
        if cb.cond is not None:
            assert isinstance(cb.cond, Score)
            if cb.false is not None:
                cmds.append(ExecuteChain().cond('if').score_range(cb.cond.__metadata__, NumRange(0, 0))
                                    .run(ReturnRun(Function(cb.false))))
            if cb.true is not None:
                cmds.append(ExecuteChain().cond('unless').score_range(cb.cond.__metadata__, NumRange(0, 0))
                                    .run(Function(cb.true)))
        return MCF(path, cmds, self.scope)

    def gen_MachJump(self, cb: MatchJump):
        path = self.scope.sub_name(cb)
        cmds = []

        def get_range(value) -> MultiRange:
            if isinstance(value, tuple | set | list):
                r = MultiRange.EMPTY
                for v in value:
                    r |= get_range(v)
                return r
            elif isinstance(value, int):
                return MultiRange(value, value)
            elif isinstance(value, _RtBaseExcMeta):
                return MultiRange(*value.errno_range)
            else:
                raise NotImplementedError

        for case in cb.cases:
            if isinstance(case, JmpEq):
                unless = False
                r = get_range(case.value)
                if len(r.valid_ranges()) > 1:
                    unless = True
                    r = ~r
            elif isinstance(case,JmpNotEq):
                unless = True
                r = get_range(case.value)
                if len((~r).valid_ranges()) == 1:
                    unless = False
                    r = ~r
            else:
                raise NotImplementedError
            chain = ExecuteChain()
            for vmin, vmax in r.valid_ranges():
                chain = chain.cond('unless' if unless else 'if').score_range(cb.flag.__metadata__, NumRange(vmin, vmax))
            cmds.append(chain.run(ReturnRun(Function(case.target))))
        return MCF(path, cmds, self.scope)

    def translate(self, cb: code_block) -> MCF:
        if isinstance(cb, BasicBlock):
            return self.gen_BasicBlcok(cb)
        elif isinstance(cb, MatchJump):
            return self.gen_MachJump(cb)
        else:
            raise NotImplementedError