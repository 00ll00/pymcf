import dis
from dis import Instruction
from types import CodeType
from typing import List, Optional, Any, Set, Iterable

from pymcf.operations import raw
from pymcf._frontend.pyops import PyOps, JMP, JABS, JMP_IF, JREL, JMP_ALWAYS


class CodeTypeRewriter:

    def __init__(self, ct: CodeType):
        self.origin = ct

        self.co_argcount = ct.co_argcount
        self.co_posonlyargcount = ct.co_posonlyargcount
        self.co_kwonlyargcount = ct.co_kwonlyargcount
        self.co_cellvars = list(ct.co_cellvars)
        self.co_freevars = list(ct.co_freevars)
        self.co_consts = list(ct.co_consts)
        self.co_names = list(ct.co_names)
        self.co_varnames = list(ct.co_varnames)
        self.co_firstlineno = ct.co_firstlineno

        cbl = CodeChain(self, Instr.wraps(dis.Bytecode(ct)))
        instrs = cbl.get_instrs()

        code = bytearray()
        lnotab = bytearray()
        last_off = 0
        last_line = self.co_firstlineno
        for instr in instrs:
            code.append(instr.opcode)
            code.append(instr.arg)
            if instr.line_code is not None and instr.line_code != last_line:
                if not -128 <= instr.offset - last_off < 128:
                    continue  # skip out range
                lnotab.append(instr.offset - last_off)
                if instr.line_code > last_line:
                    lnotab.append(instr.line_code - last_line)
                else:
                    lnotab.append(256 + instr.line_code - last_line)
                last_off = instr.offset
                last_line = instr.line_code
        code = bytes(code)
        lnotab = bytes(lnotab)

        self.codetype: CodeType = CodeType(
            self.co_argcount,
            self.co_posonlyargcount,
            self.co_kwonlyargcount,
            len(self.co_varnames),
            ct.co_stacksize + 1,
            ct.co_flags,
            code,
            tuple(self.co_consts),
            tuple(self.co_names),
            tuple(self.co_varnames),
            ct.co_filename,
            ct.co_name,
            ct.co_firstlineno,
            lnotab,
            tuple(self.co_freevars),
            tuple(self.co_cellvars)
        )

    def add_const(self, obj: Any) -> int:
        if obj not in self.co_consts:
            self.co_consts.append(obj)
        return self.co_consts.index(obj)


class Instr:

    def __init__(self, op: PyOps, arg: int = 0, line_code: Optional[int] = None,
                 offset: int = 0):
        self.op = op
        self.arg = arg
        self.offset = offset
        self.line_code = line_code

        self._jmp_target: Optional[Instr] = None
        self.jmp_froms: Set[Instr] = set()

    def __hash__(self):
        return id(self)

    @staticmethod
    def wraps(instrs: Iterable[Instruction]):
        last_line = 0
        res = []
        for instr in instrs:
            if instr.starts_line is not None:
                last_line = instr.starts_line
            res.append(
                Instr(
                    PyOps(instr.opcode),
                    instr.arg if instr.arg is not None else 0,
                    last_line,
                    instr.offset
                )
            )
        return res

    def set_jmp_targ(self, target):
        if self._jmp_target is not None:
            self._jmp_target.jmp_froms.remove(self)
        self._jmp_target = target
        target.jmp_froms.add(self)

    @property
    def jmp_from(self):
        assert len(self.jmp_froms) == 1
        return self.jmp_froms.__iter__().__next__()

    @property
    def jmp_target(self):
        return self._jmp_target

    @property
    def is_jmp_target(self):
        return len(self.jmp_froms) > 0

    @property
    def opcode(self) -> int:
        return self.op.value

    @property
    def opname(self) -> str:
        return self.op.name

    @property
    def is_jabs(self) -> bool:
        return self.op in JABS

    @property
    def is_jrel(self) -> bool:
        return self.op in JREL

    @property
    def is_jmp(self) -> bool:
        return self.op in JMP

    @property
    def is_jmp_if(self) -> bool:
        return self.op in JMP_IF

    @property
    def is_jmp_always(self) -> bool:
        return self.op in JMP_ALWAYS

    def __eq__(self, other):
        if isinstance(other, Instr):
            return self.op is other.op and self.arg == other.arg
        else:
            raise ValueError()

    def __repr__(self):
        res = f"Instr[{self.offset}]:"
        res += "       " if len(self.jmp_froms) == 0 else f"  {len(self.jmp_froms)} in "
        res += " | "
        res += "       " if self.jmp_target is None else f" to {self.jmp_target.offset} "
        res += f"| {self.op.name}, {self.arg} "
        return res


class CodeChain:
    """
    Basic chain logic code bock.
    """

    def __init__(self, pyc: CodeTypeRewriter, subs: List[Instr]):
        self.pyc = pyc
        self.subs: List[Instr] = subs
        self.final_subs: List[Instr] = []

        i = 0
        while i < len(self.subs):
            curr = self.subs[i]
            last = None if i == 0 else self.subs[i - 1]

            # (BUILD_STRING | LOAD_CONST) POP_TOP
            # convert lonely formatted string to mcfunction part
            if curr.op is PyOps.POP_TOP and last is not None and last.op in {PyOps.BUILD_STRING, PyOps.LOAD_CONST}:
                self.final_subs.extend((
                    Instr(PyOps.LOAD_CONST, self.pyc.add_const(raw)),
                    Instr(PyOps.ROT_TWO),
                    Instr(PyOps.CALL_FUNCTION, 1)
                ))

            # STORE_FAST | STORE_ATTR | STORE_SUBSCR | STORE_NAME | STORE_GLOBAL | STORE_DEREF
            #  direct Score assignment (e.g. a = 1)
            elif curr.op in {PyOps.STORE_FAST, PyOps.STORE_ATTR, PyOps.STORE_SUBSCR, PyOps.STORE_NAME, PyOps.STORE_GLOBAL, PyOps.STORE_DEREF}:
                match curr.op:
                    case PyOps.STORE_FAST:
                        self.final_subs.extend((
                            Instr(PyOps.LOAD_CONST, self.pyc.add_const(self.pyc.co_varnames[curr.arg])),
                            Instr(PyOps.LOAD_CONST, self.pyc.add_const(locals)),
                            Instr(PyOps.CALL_FUNCTION, 0),
                            Instr(PyOps.CONTAINS_OP, 0),
                    jmp1 := Instr(PyOps.POP_JUMP_IF_FALSE, +5),
                            Instr(PyOps.LOAD_FAST, curr.arg),
                            Instr(PyOps.LOAD_CONST, self.pyc.add_const(convert_assign)),
                            Instr(PyOps.ROT_THREE),
                            Instr(PyOps.CALL_FUNCTION, 2)
                        ))
                        jmp1.set_jmp_targ(curr)
                    case PyOps.STORE_GLOBAL:
                        self.final_subs.extend((
                            Instr(PyOps.LOAD_GLOBAL, curr.arg),
                            Instr(PyOps.LOAD_CONST, self.pyc.add_const(convert_assign)),
                            Instr(PyOps.ROT_THREE),
                            Instr(PyOps.CALL_FUNCTION, 2)
                        ))
                    case PyOps.STORE_ATTR:
                        self.final_subs.extend((
                            Instr(PyOps.DUP_TOP),
                            Instr(PyOps.ROT_THREE),
                            Instr(PyOps.LOAD_ATTR, curr.arg),
                            Instr(PyOps.LOAD_CONST, self.pyc.add_const(convert_assign)),
                            Instr(PyOps.ROT_THREE),
                            Instr(PyOps.CALL_FUNCTION, 2),
                            Instr(PyOps.ROT_TWO)
                        ))
                    case PyOps.STORE_SUBSCR:
                        self.final_subs.extend((
                            Instr(PyOps.DUP_TOP_TWO),
                            Instr(PyOps.ROT_N, 5),
                            Instr(PyOps.ROT_N, 5),
                            Instr(PyOps.BINARY_SUBSCR, curr.arg),
                            Instr(PyOps.LOAD_CONST, self.pyc.add_const(convert_assign)),
                            Instr(PyOps.ROT_THREE),
                            Instr(PyOps.CALL_FUNCTION, 2),
                            Instr(PyOps.ROT_THREE)
                        ))
                    # TODO convert assignment instructions
                    # case PyOps.STORE_NAME:
                    #     self.instructions.insert(i, Instr(PyOps.LOAD_NAME, curr.arg))
                    # case PyOps.STORE_DEREF:
                    #     self.instructions.insert(i, Instr(PyOps.LOAD_DEREF, curr.arg))
            self.final_subs.append(curr)
            i += 1

    def _compute_offset(self, offset):
        self.offset = offset
        i = 0
        while i < len(self.final_subs):
            instr = self.final_subs[i]
            if instr.arg >= 2 ** 8:
                for ext in (exts := gen_extended_arg(instr)):
                    self.final_subs.insert(i, ext)
                    i += 1
                    ext.offset = offset
                    offset += 2
                for jf in instr.jmp_froms:
                    jf.set_jmp_targ(exts[0])
            instr.offset = offset
            offset += 2
            i += 1
        self.end = offset

    def _compute_jmp_pos(self) -> bool:
        res = False
        i = 0
        ext_num = 0
        while i < len(self.final_subs):
            instr = self.final_subs[i]
            if instr.jmp_target is not None:
                if instr.is_jabs:
                    pos = instr.jmp_target.offset // 2
                else:
                    pos = (instr.jmp_target.offset - instr.offset) // 2 - 1
                instr.arg = pos
                exts = gen_extended_arg(instr)
                if len(exts) != ext_num:
                    res = True
                    if len(exts) == 0:
                        for jf in self.final_subs[i - ext_num].jmp_froms.copy():
                            jf.set_jmp_targ(instr)
                    else:
                        for jf in self.final_subs[i - ext_num].jmp_froms.copy():
                            jf.set_jmp_targ(exts[0])
                    for _ in range(ext_num):
                        self.final_subs.pop(i - ext_num)
                    for ext in reversed(exts):
                        self.final_subs.insert(i - ext_num, ext)
                    i = i - ext_num + len(exts)
                else:
                    for j in range(ext_num):
                        self.final_subs[i - ext_num + j].arg = exts[j].arg

            if instr.op is PyOps.EXTENDED_ARG:
                ext_num += 1
            else:
                ext_num = 0
            i += 1
        return res

    def get_instrs(self) -> List[Instr]:
        self._compute_offset(0)
        while self._compute_jmp_pos():
            self._compute_offset(self.offset)
        return self.final_subs


def convert_assign(value: Any, var: Any):
    """
    for InGameData assignment: s = 1
    """
    from pymcf.data.data import InGameData
    if isinstance(var, InGameData):
        var.set_value(value)
        return var
    else:
        return value


def gen_extended_arg(instr: Instr) -> List[Instr]:
    res = []
    arg = instr.arg
    if instr.arg >= 2 ** 32:
        raise ValueError()
    elif instr.arg >= 2 ** 24:
        res.append(Instr(PyOps.EXTENDED_ARG, arg // (2 ** 24)))
        arg %= (2 ** 24)
    elif instr.arg >= 2 ** 16:
        res.append(Instr(PyOps.EXTENDED_ARG, arg // (2 ** 16)))
        arg %= (2 ** 8)
    elif instr.arg >= 2 ** 8:
        res.append(Instr(PyOps.EXTENDED_ARG, arg // (2 ** 8)))
        arg %= (2 ** 8)
    instr.arg = arg
    return res
