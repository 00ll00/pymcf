import dis
import random
import sys
from dis import Instruction
from enum import Enum
from types import FunctionType, CodeType
from typing import List, Optional, Dict, Iterator, Any, Tuple, Set

from datas import Score
from pymcf.datas.datas import InGameData
from pymcf.code_helpers import convert_assign, finish_file, new_file, if_true_run_last_file, if_false_run_last_file
from pymcf.operations import raw
from pymcf.pyops import PyOps, JMP, JABS, NORMAL_OPS, JMP_IF, JREL
from util import ListReader


class PyCode:

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

        self.globals: Dict[str: Any] = {}

        cbl = CodeBlockList.new(self, ListReader(Instr.wrap(instr) for instr in dis.Bytecode(ct)))
        instrs = cbl.get_instrs()

        code = bytearray()
        lnotab = bytearray()
        last_off = 0
        last_line = self.co_firstlineno
        for instr in instrs:
            code.append(instr.opcode)
            code.append(instr.arg)
            if instr.line_code is not None:
                lnotab.append(instr.offset - last_off)
                lnotab.append(instr.line_code - last_line)
                last_off = instr.offset
                last_line = instr.line_code
        code = bytes(code)
        lnotab = bytes(lnotab)

        self.codetype: CodeType = CodeType(
            self.co_argcount,
            self.co_posonlyargcount,
            self.co_kwonlyargcount,
            len(self.co_varnames),
            ct.co_stacksize + 10,  # TODO compute real stack size
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

    def add_name(self, obj: Any, name: str = None) -> int:
        if name is None:
            name = "<obj_" + str(id(obj)) + ">"
        if name not in self.co_names:
            self.co_names.append(name)
            self.globals[name] = obj
        return self.co_names.index(name)

    def add_const(self, obj: Any) -> int:
        if obj not in self.co_consts:
            self.co_consts.append(obj)
        return self.co_consts.index(obj)

    def add_var(self, name: Optional[str] = None) -> int:
        if name is None:
            i = 0
            while (name := "<var_" + str(len(self.co_varnames) + i) + ">") in self.co_varnames:
                i += 1
                continue
            self.co_varnames.append(name)
        return self.co_varnames.index(name)


class Instr:

    def __init__(self, op: PyOps, arg: int = 0, line_code: Optional[int] = None,
                 offset: int = 0, is_jmp_target: bool = False):
        self.op = op
        self.arg = arg
        self.offset = offset
        self.line_code = line_code
        self.is_jmp_target = is_jmp_target

        self._jmp_target: Optional[Instr] = None
        self.jmp_from: Set[Instr] = set()

    def __hash__(self):
        return hash(self.op) ^ hash(self.arg) ^ hash(self.offset)

    @staticmethod
    def wrap(instr: Instruction):
        return Instr(
            PyOps(instr.opcode),
            instr.arg if instr.arg is not None else 0,
            instr.starts_line,
            instr.offset,
            instr.is_jump_target
        )

    def set_jmp_targ(self, target):
        if self._jmp_target is not None:
            self._jmp_target.jmp_from.remove(self)
        self._jmp_target = target
        target.jmp_from.add(self)

    @property
    def jmp_target(self):
        return self._jmp_target

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

    def __eq__(self, other):
        if isinstance(other, Instr):
            return self.op is other.op and self.arg == other.arg
        else:
            raise ValueError()

    def __repr__(self):
        return f"Instr[{self.offset}]: {self.op.name}, {self.arg}"


class CodeBlock:

    def __init__(self, pyc: PyCode, reader: ListReader[Instr], offset: int, end: int = -1):
        self.reader = reader
        self.pyc: PyCode = pyc
        self.offset: int = offset
        self.end: int = end

        self.jmp_from: Set[Instr] = set()
        self.subs: List[CodeBlock] = []

        self.parent: Optional[CodeBlock] = None

    def add_sub(self, sub):
        self.subs.append(sub)
        sub.parent = self

    @property
    def first_chain(self):
        if len(self.subs) == 0:
            return self
        else:
            return self.subs[0].first_chain

    @property
    def next(self):
        if self.parent is None:
            return None
        else:
            idx = self.parent.subs.index(self)
            if idx != len(self.parent.subs) - 1 and len(self.parent.subs) > 1:
                return self.parent.subs[idx+1]
            else:
                nxt = self.parent.next
                if nxt is None:
                    return None
                else:
                    return nxt.first_chain

    @property
    def size(self) -> int:
        """
        byte size of this block
        """
        return sum(sub.size for sub in self.subs) if len(self.subs) > 0 else 0

    def _convert_instr(self):
        for sub in self.subs:
            sub._convert_instr()

    def _compute_offset(self, offset):
        self.offset = offset
        for sub in self.subs:
            sub._compute_offset(offset)
            offset += sub.size
        self.end = offset

    def _compute_jmp_pos(self) -> bool:
        res = False
        for sub in self.subs:
            res = res or sub._compute_jmp_pos()
        return res

    def _get_instrs(self) -> List[Instr]:
        res = []
        for sub in self.subs:
            res.extend(sub._get_instrs())
        return res

    def _repr_(self, level):
        l = "  " * level
        res = l + f"{self.__class__.__name__}: {self.size} [{self.offset}, {self.end}) {{\n"
        for sub in self.subs:
            res += sub._repr_(level+1) + '\n'
        res += l + '}'
        return res

    def __repr__(self):
        return self._repr_(0)


class CodeBlockList(CodeBlock):
    """
    top level CodeBlock witch contains a list of CodeBlock.
    """

    def __init__(self, pyc: PyCode, reader: ListReader[Instr], offset: int, end: int = -1):
        super().__init__(pyc, reader, offset, end)

        while instr := reader.try_read():
            if instr.offset == end:
                reader.back()
                break
            sub = None
            match instr.op:
                case op if op in NORMAL_OPS:
                    sub = CodeChain(pyc, reader.back(), offset, end)
                case op if op in JMP_IF:
                    jmp_pair = reader[instr.jmp_target.offset//2 - 1]
                    if jmp_pair.op in JMP - JMP_IF:  # if - else - final
                        final = jmp_pair.jmp_target.offset
                        sub = CodeIfElse(pyc, instr, jmp_pair, reader, offset, final)
                    elif jmp_pair.op is PyOps.RETURN_VALUE:  # if - return - else
                        sub = CodeIfReturn(pyc, reader.back(), offset, jmp_pair.offset + 2)
                    else:  # if - final
                        sub = CodeIf(pyc, instr, reader, offset, jmp_pair.offset + 2)
                case op if op in JMP:
                    reader.back()
                    break  # consider a single jmp as a jumped else
                case PyOps.RETURN_VALUE:
                    sub = CodeReturn(pyc, instr, reader, offset, end)
            self.add_sub(sub)
            offset += sub.size

    @staticmethod
    def new(pyc: PyCode, reader: ListReader[Instr]):
        ext_arg = 0
        while instr := reader.try_read():
            if instr.op is PyOps.EXTENDED_ARG:
                ext_arg <<= 8
                ext_arg += instr.arg
            elif ext_arg > 0:
                ext_arg <<= 8
                ext_arg += instr.arg
                instr.arg = ext_arg
                ext_arg = 0

        reader.reset()
        while instr := reader.try_read():
            if instr.is_jabs:
                instr.set_jmp_targ(reader[instr.arg])
            elif instr.is_jrel or instr.op is PyOps.FOR_ITER:
                instr.set_jmp_targ(reader[instr.offset // 2 + instr.arg + 1])

        reader.reset()
        while instr := reader.try_read():
            if instr.op is PyOps.EXTENDED_ARG:
                reader.remove(instr)
                for jf in instr.jmp_from:
                    jf.set_jmp_targ(reader.now())

        reader.reset()
        return CodeBlockList(pyc, reader, 0)

    def get_instrs(self) -> List[Instr]:
        self._convert_instr()
        self._compute_offset(self.offset)
        self._compute_jmp_pos()
        return self._get_instrs()


class CodeChain(CodeBlock):
    """
    Basic chain logic code bock.
    """

    def __init__(self, pyc: PyCode, reader: ListReader[Instr], offset: int, end: int = -1, no_convert: bool = False):
        super().__init__(pyc, reader, offset, end)
        self.subs: List[Instr] = []
        self.no_convert = no_convert

        while instr := reader.try_read():
            if instr.offset == end:
                reader.back()
                break
            if self.no_convert or instr.op in NORMAL_OPS:
                self.subs.append(instr)
                offset += 2
            else:
                reader.back()
                break

    @property
    def size(self) -> int:
        return len(self.subs) * 2

    @property
    def first_chain(self):
        return self

    def _convert_instr(self):
        if self.no_convert:
            return
        """
        convert all the basic operations here (e.g. score assignment).
        """

        i = 0
        while i < len(self.subs):
            curr = self.subs[i]
            last = None if i == 0 else self.subs[i - 1]

            # (BUILD_STRING | LOAD_CONST) POP_TOP
            # convert lonely formatted string to mcfunction part
            if curr.op is PyOps.POP_TOP and last is not None and last.op in {PyOps.BUILD_STRING, PyOps.LOAD_CONST}:
                self.subs.insert(i, Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(raw)))
                self.subs.insert(i + 1, Instr(PyOps.ROT_TWO))
                self.subs.insert(i + 2, Instr(PyOps.CALL_FUNCTION, 1))
                i += 4
                continue

            # STORE_FAST | STORE_ATTR | STORE_NAME | STORE_GLOBAL | STORE_DEREF
            #  direct Score assignment (e.g. a = 1)
            if curr.op in {PyOps.STORE_FAST, PyOps.STORE_ATTR, PyOps.STORE_NAME, PyOps.STORE_GLOBAL, PyOps.STORE_DEREF}:
                match curr.op:
                    case PyOps.STORE_FAST:
                        self.subs.insert(i, Instr(PyOps.LOAD_CONST, self.pyc.add_const(self.pyc.co_varnames[curr.arg])))
                        self.subs.insert(i + 1, Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(locals, "locals")))
                        self.subs.insert(i + 2, Instr(PyOps.CALL_FUNCTION, 0))
                        self.subs.insert(i + 3, Instr(PyOps.CONTAINS_OP, 0))
                        self.subs.insert(i + 4, jmp := Instr(PyOps.POP_JUMP_IF_FALSE, +5))
                        self.subs.insert(i + 5, Instr(PyOps.LOAD_FAST, curr.arg))
                        self.subs.insert(i + 6, Instr(PyOps.LOAD_NAME, self.pyc.add_name(convert_assign)))
                        self.subs.insert(i + 7, Instr(PyOps.ROT_THREE))
                        self.subs.insert(i + 8, Instr(PyOps.CALL_FUNCTION, 2))
                        jmp.set_jmp_targ(curr)
                    case PyOps.STORE_GLOBAL:
                        self.subs.insert(i, Instr(PyOps.LOAD_GLOBAL, curr.arg))
                        self.subs.insert(i + 1, Instr(PyOps.LOAD_NAME, self.pyc.add_name(convert_assign)))
                        self.subs.insert(i + 2, Instr(PyOps.ROT_THREE))
                        self.subs.insert(i + 3, Instr(PyOps.CALL_FUNCTION, 2))
                    # TODO
                    # case PyOps.STORE_ATTR:
                    #     self.instructions.insert(i, Instr(PyOps.LOAD_ATTR, curr.arg))
                    # case PyOps.STORE_NAME:
                    #     self.instructions.insert(i, Instr(PyOps.LOAD_NAME, curr.arg))
                    # case PyOps.STORE_DEREF:
                    #     self.instructions.insert(i, Instr(PyOps.LOAD_DEREF, curr.arg))

                i += 10
                continue

            i += 1

    def _compute_offset(self, offset):
        self.offset = offset
        i = 0
        while i < len(self.subs):
            instr = self.subs[i]
            if instr.arg >= 2**8:
                for ext in (exts := gen_ext(instr)):
                    self.subs.insert(i, ext)
                    i += 1
                    ext.offset = offset
                    offset += 2
                for jf in instr.jmp_from:
                    jf.set_jmp_targ(exts[0])
            instr.offset = offset
            offset += 2
            i += 1
        self.end = offset

    def _compute_jmp_pos(self) -> bool:
        res = False
        for instr in self.subs:
            if instr.jmp_target is not None:
                if instr.is_jabs:
                    pos = instr.jmp_target.offset // 2
                else:
                    pos = (instr.jmp_target.offset - instr.offset) // 2 - 1
                instr.arg = pos
                res = res or pos >= 2**8
        return res

    def _get_instrs(self) -> List[Instr]:
        return self.subs.copy()

    def _repr_(self, level):
        l = "  " * level
        res = l + f"{self.__class__.__name__}: {self.size} [{self.offset}, {self.end}) {{\n"
        for sub in self.subs:
            res += l + "  " + sub.__repr__() + '\n'
        res += l + '}'
        return res


class CodeIfElse(CodeBlock):
    """
    if - else - final
    """

    def __init__(self, pyc: PyCode, instr_if: Instr, instr_else: Instr, reader: ListReader[Instr], offset: int,
                 end: int = -1):
        super().__init__(pyc, reader, offset, end)

        assert instr_if.op in JMP_IF
        assert instr_else.op in JMP - JMP_IF
        self.instr_if = instr_if
        self.instr_else = instr_else
        self.is_ingame_var = pyc.add_var()
        self.origin_var = pyc.add_var()

        # block if
        offset += 2
        self.blocks_if = CodeBlockList(pyc, reader, offset, instr_else.offset)
        offset += self.blocks_if.size
        self.add_sub(self.blocks_if)

        # block else
        reader.skip()
        offset += 2
        else_end = instr_else.arg * 2 if instr_else.op in JABS else (instr_else.arg + 1) * 2 + instr_else.offset
        self.blocks_else = CodeBlockList(pyc, reader, offset, else_end)
        self.add_sub(self.blocks_else)

        if reader.can_read() and (jmp := reader.read()).op in {PyOps.JUMP_FORWARD, PyOps.JUMP_ABSOLUTE}:
            assert jmp.jmp_target is self.instr_else.jmp_target
            self.instr_else.set_jmp_targ(self)
            reader.back()

    def _convert_instr(self):
        super(CodeIfElse, self)._convert_instr()

        self.subs.clear()

        # before if
        before_instrs = ListReader((
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.origin_var),
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(InGameData)),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(isinstance)),
            Instr(PyOps.ROT_THREE),
            Instr(PyOps.CALL_FUNCTION, 2),
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.is_ingame_var),
    jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, +3),
            self.instr_if,
    jmp2 := Instr(PyOps.JUMP_FORWARD, +3 or +4),
            Instr(PyOps.POP_TOP),
    tag1 := Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(new_file)),
            Instr(PyOps.CALL_FUNCTION, 0),
    tag2 := Instr(PyOps.POP_TOP)
        ))
        before_if = CodeChain(self.pyc, before_instrs, 0, end=-1, no_convert=True)
        jmp1.set_jmp_targ(tag1)
        match self.instr_if.op:
            case op if op in {PyOps.POP_JUMP_IF_TRUE, PyOps.POP_JUMP_IF_FALSE}:
                jmp2.set_jmp_targ(self.blocks_if)
            case op if op in {PyOps.JUMP_IF_TRUE_OR_POP, PyOps.JUMP_IF_FALSE_OR_POP}:
                jmp2.set_jmp_targ(tag2)
            case _:
                raise RuntimeError("unhandled jump operation")
        self.add_sub(before_if)

        # if
        self.add_sub(self.blocks_if)

        # after if
        after_if = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp3 := Instr(PyOps.POP_JUMP_IF_FALSE, +8),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(finish_file)),
                Instr(PyOps.CALL_FUNCTION, 0),
                Instr(PyOps.POP_TOP),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(if_true_run_last_file)),
                Instr(PyOps.LOAD_FAST, self.origin_var),
                Instr(PyOps.CALL_FUNCTION, 1),
                Instr(PyOps.POP_TOP),
            )),
            0,
            end=-1,
            no_convert=True
        )
        self.add_sub(after_if)

        # before else
        before_else = CodeChain(
            self.pyc,
            ListReader((
        tag3 := Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp4 := Instr(PyOps.POP_JUMP_IF_TRUE, +2),
                self.instr_else,
        tag4 := Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(new_file)),  # new mcfunction file for branch
                Instr(PyOps.CALL_FUNCTION, 0),
                Instr(PyOps.POP_TOP)
            )),
            0,
            end=-1,
            no_convert=True
        )
        jmp3.set_jmp_targ(tag3)
        jmp4.set_jmp_targ(tag4)
        self.add_sub(before_else)

        # else
        self.add_sub(self.blocks_else)

        # after else
        after_if = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp5 := Instr(PyOps.POP_JUMP_IF_FALSE, +8),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(finish_file)),
                Instr(PyOps.CALL_FUNCTION, 0),
                Instr(PyOps.POP_TOP),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(if_false_run_last_file)),
                Instr(PyOps.LOAD_FAST, self.origin_var),
                Instr(PyOps.CALL_FUNCTION, 1),
                Instr(PyOps.POP_TOP),
            )),
            0,
            end=-1,
            no_convert=True
        )
        jmp5.set_jmp_targ(self.next)
        self.add_sub(after_if)

    def _compute_jmp_pos(self):
        super(CodeIfElse, self)._compute_jmp_pos()
        if self.instr_if.is_jrel:
            self.instr_if.arg = (self.blocks_else.offset - self.instr_if.offset) // 2 - 1
        else:
            self.instr_if.arg = self.blocks_else.offset // 2
        if self.instr_else.is_jrel:
            self.instr_else.arg = (self.end - self.instr_else.offset) // 2 - 1
        else:
            self.instr_else.arg = self.end // 2


class CodeIf(CodeBlock):
    """
    if - final
    """

    def __init__(self, pyc: PyCode, instr_if: Instr, reader: ListReader[Instr], offset: int, end: int = -1):
        super().__init__(pyc, reader, offset, end)

        assert instr_if.op in JMP_IF
        self.instr_if = instr_if
        self.is_ingame_var = pyc.add_var()
        self.origin_var = pyc.add_var()

        offset += 1
        self.blocks_if = CodeBlockList(pyc, reader, offset,
                                       instr_if.arg * 2 if instr_if.op in JABS else instr_if.arg * 2 + offset)
        self.add_sub(self.blocks_if)

    def _convert_instr(self):
        super(CodeIf, self)._convert_instr()

        self.subs.clear()

        # before if
        match self.instr_if.op:
            case op if op in {PyOps.POP_JUMP_IF_TRUE, PyOps.POP_JUMP_IF_FALSE}:
                off = 4
            case op if op in {PyOps.JUMP_IF_TRUE_OR_POP, PyOps.JUMP_IF_FALSE_OR_POP}:
                off = 3
            case _:
                raise RuntimeError("unhandled jump operation")
        before_instrs = ListReader((
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.origin_var),
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(InGameData)),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(isinstance)),
            Instr(PyOps.ROT_THREE),
            Instr(PyOps.CALL_FUNCTION, 2),
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.is_ingame_var),
    jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, +3),
            self.instr_if,
            Instr(PyOps.JUMP_FORWARD, off),
            Instr(PyOps.POP_TOP),
    tag1 := Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(new_file)),
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP)
        ))
        before_if = CodeChain(self.pyc, before_instrs, 0, end=-1, no_convert=True)
        jmp1.set_jmp_targ(tag1)
        self.add_sub(before_if)

        # if
        self.add_sub(self.blocks_if)

        # after if
        after_if = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp2 := Instr(PyOps.POP_JUMP_IF_FALSE, +8),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(finish_file)),
                Instr(PyOps.CALL_FUNCTION, 0),
                Instr(PyOps.POP_TOP),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(if_true_run_last_file)),
                Instr(PyOps.LOAD_FAST, self.origin_var),
                Instr(PyOps.CALL_FUNCTION, 1),
                Instr(PyOps.POP_TOP),
            )),
            0,
            end=-1,
            no_convert=True
        )
        jmp2.set_jmp_targ(self.next)
        self.add_sub(after_if)

    def _compute_jmp_pos(self):
        super(CodeIf, self)._compute_jmp_pos()
        if self.instr_if.op in JREL:
            self.instr_if.arg = (self.blocks_if.end - self.instr_if.offset) // 2 - 1
        else:
            self.instr_if.arg = self.blocks_if.end // 2


class CodeIfReturn(CodeBlock):
    """
    if - target - else
    """

    def __init__(self, pyc: PyCode, reader: ListReader[Instr], offset: int, end: int = -1):
        super().__init__(pyc, reader, offset, end)


class CodeReturn(CodeBlock):
    """
    return
    """

    def __init__(self, pyc: PyCode, instr_ret: Instr, reader: ListReader[Instr], offset: int, end: int = -1):
        super().__init__(pyc, reader, offset, end)

        assert instr_ret.op is PyOps.RETURN_VALUE
        self.instr_ret = instr_ret

        block_ret = CodeChain(
            pyc,
            ListReader((
                self.instr_ret,
            )),
            offset,
            end=-1,
            no_convert=True
        )
        self.add_sub(block_ret)


def gen_ext(instr: Instr) -> List[Instr]:
    res = []
    arg = instr.arg
    if instr.arg >= 2**32:
        raise ValueError()
    elif instr.arg >= 2**24:
        res.append(Instr(PyOps.EXTENDED_ARG, arg//(2**24)))
        arg %= (2**24)
    elif instr.arg >= 2**16:
        res.append(Instr(PyOps.EXTENDED_ARG, arg//(2**16)))
        arg %= (2**8)
    elif instr.arg >= 2**8:
        res.append(Instr(PyOps.EXTENDED_ARG, arg//(2**8)))
        arg %= (2**8)
    instr.arg = arg
    return res