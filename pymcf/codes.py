import dis
from dis import Instruction
from types import CodeType
from typing import List, Optional, Dict, Any, Set

from pymcf import breaklevel
from pymcf.context import MCFContext
from pymcf.datas.Score import Score, ScoreEntity
from pymcf.datas.datas import InGameData
from pymcf.code_helpers import convert_assign, exit_file, new_file, convert_return, load_return_value, \
    gen_run_last_file_while, gen_run_curr_file_while, gen_set_score, gen_run_last_file, gen_run_outer_file_while, \
    gen_run_outer_file, gen_set_score_value_while, gen_exit_files_until, get_current_file
from pymcf.operations import raw
from pymcf.pyops import PyOps, JMP, JABS, NORMAL_OPS, JMP_IF, JREL, JMP_ALWAYS
from pymcf.util import ListReader


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

        self.globals: Dict[str: Any] = {}

        cbl = CodeBlockList.new(self, ListReader(Instr.wrap(instr) for instr in dis.Bytecode(ct)))
        instrs = cbl.get_instrs()

        code = bytearray()
        lnotab = bytearray()
        last_off = 0
        last_line = self.co_firstlineno + 1  # TODO why CodeType auto increase line number by 1
        for instr in instrs:
            code.append(instr.opcode)
            code.append(instr.arg)
            if instr.line_code is not None:
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
            name = "<obj_" + hex(id(obj)) + ">"
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
                 offset: int = 0):
        self.op = op
        self.arg = arg
        self.offset = offset
        self.line_code = line_code

        self._jmp_target: Optional[Instr | AbstractCodeBlock] = None
        self.jmp_froms: Set[Instr] = set()

    def __hash__(self):
        return id(self)

    @staticmethod
    def wrap(instr: Instruction):
        return Instr(
            PyOps(instr.opcode),
            instr.arg if instr.arg is not None else 0,
            instr.starts_line,
            instr.offset
        )

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


class AbstractCodeBlock:

    def __init__(self, pyc: CodeTypeRewriter, reader: ListReader[Instr], offset: int, end: int = -1, base_size: int = 0, as_file: bool = True, dbg_name=None):
        self.reader = reader
        self.pyc: CodeTypeRewriter = pyc
        self.offset: int = offset
        self.end: int = end
        self.base_size: int = base_size
        self.as_file = as_file
        self.dbg_name = dbg_name

        self.jmp_froms: Set[Instr] = set()
        self.subs: List[AbstractCodeBlock] = []
        self.final_subs: List[AbstractCodeBlock] = []

        self._brk_flag: Optional[Score] = None
        self._brk_flags: Set[Score] = set()
        self._brk_level: int = breaklevel.NONE
        self._brk_capture_level: int = breaklevel.NONE
        self.loop_file: Optional[int] = None
        self.is_ingame_var: Optional[int] = None

        self.parent: Optional[AbstractCodeBlock] = None

    def add_sub(self, sub):
        self.subs.append(sub)
        sub.parent = self

    def add_final_sub_and_convert(self, sub, add_call: bool = True):
        self.final_subs.append(sub)
        sub.parent = self
        if sub.as_file and add_call:
            self.append_call_last_with_flag_check()
        sub._convert_instr()

    @property
    def brk_flags(self) -> Set[Score]:
        """
        get last brk flag var of this codeblock
        """
        return self._brk_flags.copy()

    def make_break_handler(self, level: int):
        self._brk_flag = new_brk()
        self._brk_capture_level = level

    def on_break(self, level: int) -> Score:
        """
        get the break flag for this break operation, and record it to self.brk_flags dynamically
        when a break created with a level not higher than _brk_level of current block, it will be captured,
        otherwise it will be passed to the parent block
        """
        if level <= self._brk_capture_level and self._brk_flag is not None:
            brk = self._brk_flag
        else:
            brk = self.parent.on_break(level)
        self._brk_flags.add(brk)
        return brk

    def get_is_ingame_var(self, level: int) -> int:
        """
        get last break acceptable block's is_ingame_var
        """
        if level <= self._brk_capture_level and self.is_ingame_var is not None:
            return self.is_ingame_var
        else:
            return self.parent.get_is_ingame_var(level)

    def get_loop_file(self, level: int) -> int:
        """
        get last break acceptable block's file var
        """
        if level <= self._brk_capture_level and self.loop_file is not None:
            return self.loop_file
        else:
            return self.parent.get_loop_file(level)

    def append_call_last_with_flag_check(self):
        self.final_subs.append(
            chain := CodeChain(
                self.pyc,
                ListReader((
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file(self.brk_flags))),
                    Instr(PyOps.CALL_FUNCTION, 0),
                    Instr(PyOps.POP_TOP)
                )),
                0, end=-1, no_convert=True, as_file=False, dbg_name="call last file with flag check"
            )
        )
        chain._convert_instr()

    @property
    def jmp_from(self):
        assert len(self.jmp_froms) == 1
        return self.jmp_froms.__iter__().__next__()

    @property
    def first_chain(self):
        if len(self.subs) == 0:
            return self
        else:
            return self.subs[0].first_chain

    @property
    def next(self):
        """
        next code block of self
        use in _convert_instr() only
        """
        if self.parent is None:
            return None
        else:
            idx = self.parent.subs.index(self)
            if idx != len(self.parent.subs) - 1 and len(self.parent.subs) > 1:
                return self.parent.subs[idx + 1]
            else:
                nxt = self.parent.next
                if nxt is None:
                    return None
                else:
                    return nxt.first_chain

    @property
    def last(self):
        """
        last sub in self.final_subs
        use in _convert_instr() only
        """
        return self.final_subs[-1]

    @property
    def size(self) -> int:
        """
        byte size of this block
        """
        subs = self.final_subs if len(self.final_subs) > 0 else self.subs
        res = sum(sub.size for sub in subs)
        return res if res > self.base_size else self.base_size

    def _insert_new_file(self):
        if self.as_file:
            self.final_subs.insert(
                0,
                chain1 := CodeChain(
                    self.pyc,
                    ListReader((
                        Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(new_file)),
                        Instr(PyOps.CALL_FUNCTION, 0),
                        Instr(PyOps.POP_TOP)
                    )),
                    0, -1, no_convert=True, as_file=False, dbg_name="new file"
                )
            )
            chain1._convert_instr()

    def _insert_exit_file(self):
        if self.as_file:
            self.final_subs.append(
                chain2 := CodeChain(
                    self.pyc,
                    ListReader((
                        Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(exit_file)),
                        Instr(PyOps.CALL_FUNCTION, 0),
                        Instr(PyOps.POP_TOP)
                    )),
                    0, -1, no_convert=True, as_file=False, dbg_name="exit file"
                )
            )
            chain2._convert_instr()

    def _insert_ingamedata_check(self):
        """
        before:     TOS: origin var

        after:      TOS: ingame var     TOS1: origin var
        """
        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    Instr(PyOps.DUP_TOP),
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(InGameData)),
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(isinstance)),
                    Instr(PyOps.ROT_THREE),
                    Instr(PyOps.CALL_FUNCTION, 2)
                )),
                0, -1, no_convert=True, as_file=False, dbg_name="check data ingame"
            )
        )

    def _convert_instr(self):
        raise NotImplementedError()

    def _compute_offset(self, offset):
        self.offset = offset
        for sub in self.final_subs:
            sub._compute_offset(offset)
            offset += sub.size
        self.end = offset

    def _compute_jmp_pos(self) -> bool:
        res = False
        for sub in self.final_subs:
            res = res or sub._compute_jmp_pos()
        return res

    def _get_instrs(self) -> List[Instr]:
        res = []
        for sub in self.final_subs:
            res.extend(sub._get_instrs())
        return res

    def _repr_(self, level):
        l = "  " * level
        res = l + f"{self.__class__.__name__}: {self.dbg_name} [{self.offset}, {self.end}) {{\n"
        for sub in self.final_subs:
            res += sub._repr_(level + 1) + '\n'
        res += l + '}'
        return res

    def __repr__(self):
        return self._repr_(0)


class CodeBlockList(AbstractCodeBlock):
    """
    top level CodeBlock witch contains a list of CodeBlock.
    """

    def __init__(self, pyc: CodeTypeRewriter, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, as_file=as_file, dbg_name=dbg_name)

        while instr := reader.try_read():
            if instr.offset == end:
                reader.back()
                break
            sub = None
            if instr.is_jmp_target:
                i = 1
                while next_jmp := reader.seek(i):
                    if not next_jmp.is_jmp:
                        i += 1
                    else:
                        break

                if next_jmp is not None:
                    # compacted while ...
                    while_pair = sorted(instr.jmp_froms, key=lambda i: i.offset, reverse=True)[0]
                    if next_jmp.is_jmp_if and next_jmp.jmp_target.offset > while_pair.offset:
                        sub = CodeCompactedWhile(pyc, next_jmp, while_pair, reader, offset, while_pair.offset + 2)
                        self.add_sub(sub)
                        offset += sub.size
                        continue

            match instr.op:
                case op if op in NORMAL_OPS:
                    sub = CodeChain(pyc, reader.back(), offset, end)
                case op if op in JMP_IF:
                    if 0 <= end < instr.jmp_target.offset:
                        # break if
                        sub = CodeBreakIf(pyc, instr, reader, offset, instr.offset + 2)
                    elif instr.jmp_target.offset < offset:
                        # continue if
                        sub = CodeContinueIf(pyc, instr, reader, offset, instr.offset + 2)
                    else:
                        instr_next = reader[instr.offset // 2 + 1]
                        jmp_pair = reader[instr.jmp_target.offset // 2 - 1]

                        # while ...
                        if len(instr_next.jmp_froms) == 1 and jmp_pair.offset >= instr_next.jmp_from.offset > instr_next.offset:
                            sub = CodeWhile(pyc, instr, instr_next.jmp_from, reader, offset, jmp_pair.offset + 2)

                        # if - else - final
                        elif jmp_pair.op in JMP_ALWAYS and instr.offset <= jmp_pair.jmp_target.offset < end:
                            final = jmp_pair.jmp_target.offset
                            sub = CodeIfElse(pyc, instr, jmp_pair, reader, offset, final)

                        # if - final
                        else:
                            sub = CodeIf(pyc, instr, reader, offset, jmp_pair.offset + 2)
                case op if op in JMP:
                    if offset < instr.jmp_target.offset <= end and end >= 0:
                        reader.back()
                        break  # consider a single jmp as a jumped else TODO: break and continue
                    elif 0 <= end < instr.jmp_target.offset:  # break
                        sub = CodeBreak(pyc, instr, reader, offset, instr.offset + 2)
                    elif instr.jmp_target.offset < offset:  # continue
                        sub = CodeContinue(pyc, instr, reader, offset, instr.offset + 2)
                    else:
                        raise RuntimeError("unhandled jump")

                case PyOps.FOR_ITER:
                    for_pair = sorted(instr.jmp_froms, key=lambda i: i.offset, reverse=True)[0]
                    sub = CodeFor(pyc, instr, for_pair, reader, offset, for_pair.offset)
                case PyOps.RETURN_VALUE:
                    sub = CodeReturn(pyc, instr, reader, offset, end)
                case op if op in {PyOps.RAISE_VARARGS, PyOps.RERAISE}:
                    sub = CodeRaise(pyc, instr, reader, offset, end)
            self.add_sub(sub)
            offset += sub.size

    def _convert_instr(self):
        if self.as_file:
            self._insert_new_file()
        for sub in self.subs:
            self.add_final_sub_and_convert(sub)
        if self.as_file:
            self._insert_exit_file()

    @staticmethod
    def new(pyc: CodeTypeRewriter, reader: ListReader[Instr]):
        # decode extended arg
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

        # build jump relationship
        reader.reset()
        while instr := reader.try_read():
            if instr.is_jabs:
                instr.set_jmp_targ(reader[instr.arg])
            elif instr.is_jrel or instr.op is PyOps.FOR_ITER:
                instr.set_jmp_targ(reader[instr.offset // 2 + instr.arg + 1])

        # remove extended arg
        reader.reset()
        while instr := reader.try_read():
            if instr.op is PyOps.EXTENDED_ARG:
                reader.remove(instr)
                for jf in instr.jmp_froms:
                    jf.set_jmp_targ(reader.now())

        # build cbl
        reader.reset()
        cbl = CodeBlockList(pyc, reader, 0)
        cbl.make_break_handler(breaklevel.RETURN)

        return cbl

    def get_instrs(self) -> List[Instr]:
        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_set_score(self._brk_flag, 0))),
                    Instr(PyOps.CALL_FUNCTION, 0),
                    Instr(PyOps.POP_TOP)
                )),
                0,
                end=-1, no_convert=True, as_file=False, dbg_name="set top level break flag"
            )
        )
        self._convert_instr()
        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(load_return_value)),
                    Instr(PyOps.CALL_FUNCTION, 0),
                    Instr(PyOps.RETURN_VALUE)
                )),
                self.offset + self.size,
                end=-1, no_convert=True, as_file=False, dbg_name="load_ret_val"
            )
        )
        self._compute_offset(self.offset)
        while self._compute_jmp_pos():
            self._compute_offset(self.offset)
        return self._get_instrs()


class CodeChain(AbstractCodeBlock):
    """
    Basic chain logic code bock.
    """

    def __init__(self, pyc: CodeTypeRewriter, reader: ListReader[Instr], offset: int, end: int = -1, no_convert: bool = False, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, as_file=as_file, dbg_name=f"{dbg_name} <as_file: {as_file}>")
        self.subs: List[Instr] = []
        self.final_subs: List[Instr] = []
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

    def append_call_last_with_flag_check(self):
        """
        do nothing for code chain
        """
        return

    @property
    def size(self) -> int:
        if len(self.final_subs) > 0:
            return len(self.final_subs) * 2
        else:
            return len(self.subs) * 2

    @property
    def first_chain(self):
        return self

    def _convert_instr(self):  # no super call
        if self.no_convert:
            self.final_subs = self.subs
        else:
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
                    self.final_subs.extend((
                        Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(raw)),
                        Instr(PyOps.ROT_TWO),
                        Instr(PyOps.CALL_FUNCTION, 1)
                    ))

                # STORE_FAST | STORE_ATTR | STORE_NAME | STORE_GLOBAL | STORE_DEREF
                #  direct Score assignment (e.g. a = 1)
                elif curr.op in {PyOps.STORE_FAST, PyOps.STORE_ATTR, PyOps.STORE_NAME, PyOps.STORE_GLOBAL, PyOps.STORE_DEREF}:
                    match curr.op:
                        case PyOps.STORE_FAST:
                            self.final_subs.extend((
                                Instr(PyOps.LOAD_CONST, self.pyc.add_const(self.pyc.co_varnames[curr.arg])),
                                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(locals, "locals")),
                                Instr(PyOps.CALL_FUNCTION, 0),
                                Instr(PyOps.CONTAINS_OP, 0),
                        jmp1 := Instr(PyOps.POP_JUMP_IF_FALSE, +5),
                                Instr(PyOps.LOAD_FAST, curr.arg),
                                Instr(PyOps.LOAD_NAME, self.pyc.add_name(convert_assign)),
                                Instr(PyOps.ROT_THREE),
                                Instr(PyOps.CALL_FUNCTION, 2)
                            ))
                            jmp1.set_jmp_targ(curr)
                        case PyOps.STORE_GLOBAL:
                            self.subs.extend((
                                Instr(PyOps.LOAD_GLOBAL, curr.arg),
                                Instr(PyOps.LOAD_NAME, self.pyc.add_name(convert_assign)),
                                Instr(PyOps.ROT_THREE),
                                Instr(PyOps.CALL_FUNCTION, 2)
                            ))
                        case PyOps.STORE_ATTR:
                            self.subs.extend((
                                Instr(PyOps.LOAD_ATTR, curr.arg),
                                Instr(PyOps.LOAD_NAME, self.pyc.add_name(convert_assign)),
                                Instr(PyOps.ROT_THREE),
                                Instr(PyOps.CALL_FUNCTION, 2)
                            ))
                        # TODO
                        # case PyOps.STORE_ATTR:
                        #     self.instructions.insert(i, Instr(PyOps.LOAD_ATTR, curr.arg))
                        # case PyOps.STORE_NAME:
                        #     self.instructions.insert(i, Instr(PyOps.LOAD_NAME, curr.arg))
                        # case PyOps.STORE_DEREF:
                        #     self.instructions.insert(i, Instr(PyOps.LOAD_DEREF, curr.arg))
                self.final_subs.append(curr)
                i += 1

        if self.as_file:
            self.final_subs = [
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(new_file)),
                Instr(PyOps.CALL_FUNCTION, 0),
                Instr(PyOps.POP_TOP)
            ] + self.final_subs + [
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(exit_file)),
                Instr(PyOps.CALL_FUNCTION, 0),
                Instr(PyOps.POP_TOP)
            ]

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
                        for jf in self.final_subs[i - ext_num].jmp_froms:
                            jf.set_jmp_targ(instr)
                    else:
                        for jf in self.final_subs[i - ext_num].jmp_froms:
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

    def _get_instrs(self) -> List[Instr]:
        return self.final_subs.copy()

    def _repr_(self, level):
        l = "  " * level
        res = l + f"{self.__class__.__name__}: {self.dbg_name} [{self.offset}, {self.end}) {{\n"
        for sub in self.final_subs:
            res += l + "  " + sub.__repr__() + '\n'
        res += l + '}'
        return res


class CodeIfElse(AbstractCodeBlock):
    """
    if - else - final
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_if: Instr, instr_else: Instr, reader: ListReader[Instr], offset: int,
                 end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 4, as_file=as_file, dbg_name=dbg_name)

        assert instr_if.op in JMP_IF
        assert instr_else.op in JMP - JMP_IF
        assert self.as_file
        self.instr_if = instr_if
        self.instr_else = instr_else
        self.is_ingame_var = pyc.add_var()
        self.origin_var = pyc.add_var()

        self.if_true = self.instr_if.op in {PyOps.POP_JUMP_IF_FALSE, PyOps.JUMP_IF_FALSE_OR_POP}

        # block if
        offset += 2
        self.blocks_if = CodeBlockList(pyc, reader, offset, instr_else.offset, dbg_name="blocks if")
        offset += self.blocks_if.size
        self.add_sub(self.blocks_if)

        # block else
        reader.skip()
        offset += 2
        else_end = instr_else.arg * 2 if instr_else.op in JABS else (instr_else.arg + 1) * 2 + instr_else.offset
        self.blocks_else = CodeBlockList(pyc, reader, offset, else_end, dbg_name="blocks else")
        self.add_sub(self.blocks_else)

        if reader.can_read() and (jmp := reader.now()).op in {PyOps.JUMP_FORWARD, PyOps.JUMP_ABSOLUTE}:
            assert jmp.jmp_target is self.instr_else.jmp_target
            self.instr_else.set_jmp_targ(jmp)

    def _convert_instr(self):

        self.final_subs.clear()

        self._insert_new_file()

        self._insert_ingamedata_check()

        # before if
        before_instrs = ListReader((
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.is_ingame_var),
    jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, ),

            self.instr_if,
    jmp2 := Instr(PyOps.JUMP_FORWARD, ),

    tag1 := Instr(PyOps.STORE_FAST, self.origin_var),
    jmp3 := Instr(PyOps.JUMP_FORWARD, ),
            Instr(PyOps.POP_TOP)
        ))
        before_if = CodeChain(self.pyc, before_instrs, 0, end=-1, no_convert=True, as_file=False, dbg_name="before if")
        jmp1.set_jmp_targ(tag1)
        jmp3.set_jmp_targ(self.blocks_if)
        jmp2.set_jmp_targ(self.blocks_if)
        self.add_final_sub_and_convert(before_if)

        # if
        assert self.blocks_if.as_file
        self.add_final_sub_and_convert(self.blocks_if, add_call=False)

        # after if
        after_if = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp4 := Instr(PyOps.POP_JUMP_IF_FALSE, ),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file_while(self.if_true, self.brk_flags))),
                Instr(PyOps.LOAD_FAST, self.origin_var),
                Instr(PyOps.CALL_FUNCTION, 1),
                Instr(PyOps.POP_TOP),
            )), 0, end=-1, no_convert=True, as_file=False, dbg_name="after if"
        )
        self.add_final_sub_and_convert(after_if)

        # before else
        before_else = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp5 := Instr(PyOps.POP_JUMP_IF_TRUE, ),
                self.instr_else
            )), 0, end=-1,  no_convert=True, as_file=False, dbg_name="before else"
        )
        jmp4.set_jmp_targ(before_else)
        jmp5.set_jmp_targ(self.blocks_else)
        self.add_final_sub_and_convert(before_else)

        # else
        assert self.blocks_else.as_file
        self.add_final_sub_and_convert(self.blocks_else, add_call=False)

        # after else
        after_if = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp6 := Instr(PyOps.POP_JUMP_IF_FALSE, ),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file_while(not self.if_true, self.brk_flags))),
                Instr(PyOps.LOAD_FAST, self.origin_var),
                Instr(PyOps.CALL_FUNCTION, 1),
                Instr(PyOps.POP_TOP),
            )), 0, end=-1, no_convert=True, as_file=False, dbg_name="after else"
        )
        self.add_final_sub_and_convert(after_if)

        self._insert_exit_file()

        jmp6.set_jmp_targ(self.last)

        self.instr_if.set_jmp_targ(self.blocks_else)
        self.instr_else.set_jmp_targ(self.last)


class CodeIf(AbstractCodeBlock):
    """
    if - final
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_if: Instr, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 2, as_file=as_file, dbg_name=dbg_name)

        assert instr_if.op in JMP_IF
        assert self.as_file
        self.instr_if = instr_if
        self.is_ingame_var = pyc.add_var()
        self.origin_var = pyc.add_var()

        self.if_true = self.instr_if.op in {PyOps.POP_JUMP_IF_FALSE, PyOps.JUMP_IF_FALSE_OR_POP}

        offset += 2
        self.blocks_if = CodeBlockList(pyc, reader, offset, instr_if.jmp_target.offset, dbg_name="blocks if")
        self.add_sub(self.blocks_if)

    def _convert_instr(self):

        self.final_subs.clear()

        self._insert_new_file()

        self._insert_ingamedata_check()

        # before if
        before_instrs = ListReader((
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.is_ingame_var),

    jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, ),
            self.instr_if,

    jmp2 := Instr(PyOps.JUMP_FORWARD, ),
    tag1 := Instr(PyOps.STORE_FAST, self.origin_var),
    jmp3 := Instr(PyOps.JUMP_FORWARD, ),
            Instr(PyOps.POP_TOP)
        ))
        before_if = CodeChain(self.pyc, before_instrs, 0, end=-1, no_convert=True, as_file=False, dbg_name="before if")
        jmp1.set_jmp_targ(tag1)
        jmp3.set_jmp_targ(self.blocks_if)
        jmp2.set_jmp_targ(self.blocks_if)
        self.add_final_sub_and_convert(before_if)

        # if
        assert self.blocks_if.as_file
        self.add_final_sub_and_convert(self.blocks_if, add_call=False)

        # after if
        after_if = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_FAST, self.is_ingame_var),
        jmp4 := Instr(PyOps.POP_JUMP_IF_FALSE, ),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file_while(self.if_true, self.brk_flags))),
                Instr(PyOps.LOAD_FAST, self.origin_var),
                Instr(PyOps.CALL_FUNCTION, 1),
                Instr(PyOps.POP_TOP),
            )), 0, end=-1, no_convert=True, as_file=False, dbg_name="after if"
        )
        self.add_final_sub_and_convert(after_if)

        self._insert_exit_file()

        jmp4.set_jmp_targ(self.last)
        self.instr_if.set_jmp_targ(self.last)


class CodeWhile(AbstractCodeBlock):
    """
    (compute condition) while (...) (compute condition) (jump to while)
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_while: Instr, instr_loop: Instr, reader: ListReader[Instr], offset: int,
                 end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 4, as_file=as_file, dbg_name=dbg_name)

        assert self.as_file

        self.make_break_handler(breaklevel.BREAK)

        self.instr_while = instr_while
        self.instr_loop = instr_loop
        self.is_ingame_var = pyc.add_var()
        self.ingame_var = pyc.add_var()
        self.loop_file = self.pyc.add_var()

        self.while_true = self.instr_while.op in {PyOps.POP_JUMP_IF_FALSE, PyOps.JUMP_IF_FALSE_OR_POP}
        self.loop_true = self.instr_loop.op in {PyOps.POP_JUMP_IF_TRUE, PyOps.JUMP_IF_TRUE_OR_POP}

        offset += 2
        self.blocks_loop = CodeBlockList(pyc, reader, offset, self.instr_loop.offset, as_file=False, dbg_name="loop body")
        self.add_sub(self.blocks_loop)
        reader.skip()
        offset += self.blocks_loop.size + 2

        if self.instr_while.jmp_target.offset > self.instr_loop.offset + 2:
            self.remaining = CodeBlockList(pyc, reader, offset, self.instr_while.jmp_target.offset)
            self.add_sub(self.remaining)
        else:
            self.remaining = None

    def _convert_instr(self):

        self.final_subs.clear()

        self._insert_new_file()

        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(get_current_file)),
                    Instr(PyOps.CALL_FUNCTION, 0),
                    Instr(PyOps.STORE_FAST, self.loop_file),
                )),
                0, end=-1, no_convert=True, as_file=False
            )
        )

        self._insert_ingamedata_check()

        # before loop
        before_instrs = ListReader((
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.is_ingame_var),
    jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, ),  # jump to ingame code if ingame

            self.instr_while,  # origin jump
    jmp2 := Instr(PyOps.JUMP_FORWARD, ),  # skip ingame code if not ingame

            # ingame codes
    tag1 := Instr(PyOps.STORE_FAST, self.ingame_var),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_set_score(self._brk_flag, 0))),  # set brk flag
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(new_file)),  # new file
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP)
        ))
        before_loop = CodeChain(self.pyc, before_instrs, 0, end=-1, no_convert=True, as_file=False, dbg_name="before while")
        jmp1.set_jmp_targ(tag1)
        jmp2.set_jmp_targ(self.blocks_loop)
        self.add_final_sub_and_convert(before_loop)

        # while
        assert not self.blocks_loop.as_file
        self.add_final_sub_and_convert(self.blocks_loop, add_call=False)

        self._insert_ingamedata_check()

        # after loop
        after_instrs = ListReader((
    jmp4 := Instr(PyOps.POP_JUMP_IF_TRUE, ),  # skip origin loop jump if ingame

            self.instr_loop,  # origin jump
    jmp5 := Instr(PyOps.JUMP_FORWARD, ),  # skip ingame codes if not ingame

            # ingame codes
    tag4 := Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_curr_file_while(self.loop_true, self.brk_flags, self._brk_capture_level))),
            Instr(PyOps.ROT_TWO),
            Instr(PyOps.CALL_FUNCTION, 1),
            Instr(PyOps.POP_TOP),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(exit_file)),  # exit file (loop content)
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP),

    tag5 := Instr(PyOps.LOAD_FAST, self.is_ingame_var),
    jmp6 := Instr(PyOps.POP_JUMP_IF_FALSE, ),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file_while(self.loop_true, self.brk_flags))),
            Instr(PyOps.LOAD_FAST, self.ingame_var),
            Instr(PyOps.CALL_FUNCTION, 1),
            Instr(PyOps.POP_TOP)
        ))
        jmp4.set_jmp_targ(tag4)
        jmp5.set_jmp_targ(tag5)
        self.instr_loop.set_jmp_targ(self.blocks_loop)
        after_loop = CodeChain(self.pyc, after_instrs, 0, end=-1, no_convert=True, as_file=False, dbg_name="after loop")
        self.add_final_sub_and_convert(after_loop)

        if self.remaining is not None:
            self.add_final_sub_and_convert(self.remaining)

        self._insert_exit_file()

        self.instr_while.set_jmp_targ(self.last)
        jmp6.set_jmp_targ(self.last)


class CodeCompactedWhile(AbstractCodeBlock):
    """
    (compute condition) while (...) (jump to head)
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_while: Instr, instr_loop: Instr, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 4, as_file=as_file, dbg_name=dbg_name)

        assert self.as_file
        assert instr_loop.op in JMP_ALWAYS

        self.instr_while = instr_while
        self.instr_loop = instr_loop
        self.is_ingame_var = pyc.add_var()
        self.ingame_var = pyc.add_var()

        self.while_true = self.instr_while.op in {PyOps.POP_JUMP_IF_FALSE, PyOps.JUMP_IF_FALSE_OR_POP}

        self.block_condition = CodeChain(pyc, reader, offset, instr_while.offset, no_convert=True, as_file=False, dbg_name="compute condition")
        self.add_sub(self.block_condition)

        offset += self.block_condition.size + 2
        reader.skip()
        self.blocks_loop = CodeBlockList(pyc, reader, offset, instr_loop.offset, as_file=False, dbg_name="loop body")
        self.add_sub(self.blocks_loop)
        reader.skip()

    def _convert_instr(self):

        self.final_subs.clear()

        self._insert_new_file()

        self.add_sub(self.block_condition)

        self._insert_ingamedata_check()

        # before loop
        before_instrs = ListReader((
            Instr(PyOps.DUP_TOP),
            Instr(PyOps.STORE_FAST, self.is_ingame_var),
    jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, ),  # jump to ingame code if ingame

            self.instr_while,  # origin jump
    jmp2 := Instr(PyOps.JUMP_FORWARD, ),  # skip ingame code if not ingame

            # ingame codes
    tag1 := Instr(PyOps.STORE_FAST, self.ingame_var),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_set_score(self._brk_flag, 0))),  # set brk flag
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(new_file)),  # new file
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP)
        ))
        before_loop = CodeChain(self.pyc, before_instrs, 0, end=-1, no_convert=True, as_file=False,
                                dbg_name="before while")
        jmp1.set_jmp_targ(tag1)
        jmp2.set_jmp_targ(self.blocks_loop)
        self.add_final_sub_and_convert(before_loop)

        # while
        assert not self.blocks_loop.as_file
        self.add_final_sub_and_convert(self.blocks_loop, add_call=False)

        # after loop
        after_instrs = ListReader((
    jmp4 := Instr(PyOps.POP_JUMP_IF_TRUE, ),  # skip origin loop jump if ingame

            self.instr_loop,  # origin jump
    jmp5 := Instr(PyOps.JUMP_FORWARD, ),  # skip ingame codes if not ingame

            # ingame codes
    tag4 := Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_outer_file(self.brk_flags, self._brk_capture_level))),
            Instr(PyOps.LOAD_FAST, self.ingame_var),
            Instr(PyOps.CALL_FUNCTION, 1),
            Instr(PyOps.POP_TOP),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(exit_file)),  # exit file (loop content)
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP),

    tag5 := Instr(PyOps.LOAD_FAST, self.is_ingame_var),
    jmp6 := Instr(PyOps.POP_JUMP_IF_FALSE, ),
            Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file(self.brk_flags))),
            Instr(PyOps.LOAD_FAST, self.ingame_var),
            Instr(PyOps.CALL_FUNCTION, 1),
            Instr(PyOps.POP_TOP)
        ))
        jmp4.set_jmp_targ(tag4)
        jmp5.set_jmp_targ(tag5)
        self.instr_loop.set_jmp_targ(self.block_condition)

        after_loop = CodeChain(self.pyc, after_instrs, 0, end=-1, no_convert=True, as_file=False, dbg_name="after loop")
        self.add_final_sub_and_convert(after_loop)

        self._insert_exit_file()

        self.instr_while.set_jmp_targ(self.last)
        jmp6.set_jmp_targ(self.last)


class CodeFor(AbstractCodeBlock):
    """
    for ...
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_for: Instr, instr_loop: Instr, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 4, as_file=as_file, dbg_name=dbg_name)

        self.instr_for = instr_for
        self.instr_loop = instr_loop

        # TODO

    def _convert_instr(self):
        pass


class CodeBreakIf(AbstractCodeBlock):
    """
    if ... break

    break level: BREAK
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_if: Instr, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 2, as_file=as_file, dbg_name=dbg_name)

        self._brk_level = breaklevel.BREAK

        self.instr_if = instr_if
        self.if_true = self.instr_if.op in {PyOps.POP_JUMP_IF_TRUE, PyOps.JUMP_IF_TRUE_OR_POP}

        self.origin = self.pyc.add_var()

    def _convert_instr(self):

        if self.as_file:
            self._insert_new_file()

        self._insert_ingamedata_check()

        # before break
        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
            jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, ),
                    self.instr_if,
            jmp3 := Instr(PyOps.JUMP_FORWARD, ),
            tag1 := Instr(PyOps.STORE_FAST, self.origin),
                )),
                0, end=-1, no_convert=True, as_file=False, dbg_name="before break"
            )
        )
        jmp1.set_jmp_targ(tag1)

        # break
        self.add_final_sub_and_convert(
    tag0 := CodeBreak(
                self.pyc,
        jmp2 := Instr(PyOps.JUMP_ABSOLUTE, ),
                ListReader(()),
                0, end=-1, as_file=True, dbg_name="inner break"
            ),
            add_call=False
        )
        jmp2.set_jmp_targ(self.instr_if.jmp_target)
        self.instr_if.set_jmp_targ(tag0)

        # after break
        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file_while(self.if_true, self.brk_flags))),
                    Instr(PyOps.LOAD_FAST, self.origin),
                    Instr(PyOps.CALL_FUNCTION, 1),
                    Instr(PyOps.POP_TOP)
                )),
                0, end=-1, no_convert=True, as_file=False, dbg_name="after break"
            )
        )

        if self.as_file:
            self._insert_exit_file()
            jmp3.set_jmp_targ(self.last)
        else:
            jmp3.set_jmp_targ(self.next)


class CodeContinueIf(AbstractCodeBlock):
    """
    if ... continue

    break level: CONTINUE
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_if: Instr, reader: ListReader[Instr], offset: int, end: int = -1,
                 as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 2, as_file=as_file, dbg_name=dbg_name)

        self._brk_level = breaklevel.CONTINUE

        self.instr_if = instr_if
        self.if_true = self.instr_if.op in {PyOps.POP_JUMP_IF_TRUE, PyOps.JUMP_IF_TRUE_OR_POP}

        self.origin = self.pyc.add_var()

    def _convert_instr(self):

        if self.as_file:
            self._insert_new_file()

        self._insert_ingamedata_check()

        # before continue
        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, ),
                    self.instr_if,
                    jmp3 := Instr(PyOps.JUMP_FORWARD, ),
                    tag1 := Instr(PyOps.STORE_FAST, self.origin),
                )),
                0, end=-1, no_convert=True, as_file=False, dbg_name="before continue"
            )
        )
        jmp1.set_jmp_targ(tag1)

        # continue
        self.add_final_sub_and_convert(
            tag0 := CodeContinue(
                self.pyc,
                jmp2 := Instr(PyOps.JUMP_ABSOLUTE, ),
                ListReader(()),
                0, end=-1, as_file=True, dbg_name="inner continue"
            ),
            add_call=False
        )
        jmp2.set_jmp_targ(self.instr_if.jmp_target)
        self.instr_if.set_jmp_targ(tag0)

        # after continue
        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_run_last_file_while(self.if_true, self.brk_flags))),
                    Instr(PyOps.LOAD_FAST, self.origin),
                    Instr(PyOps.CALL_FUNCTION, 1),
                    Instr(PyOps.POP_TOP)
                )),
                0, end=-1, no_convert=True, as_file=False, dbg_name="after continue"
            )
        )

        if self.as_file:
            self._insert_exit_file()
            jmp3.set_jmp_targ(self.last)
        else:
            jmp3.set_jmp_targ(self.next)


class CodeBreak(AbstractCodeBlock):
    """
    break

    break level: BREAK
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_jmp: Instr, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 2, as_file=as_file, dbg_name=dbg_name)

        assert instr_jmp.op in JMP_ALWAYS

        self._brk_level = breaklevel.BREAK

        self.instr_jmp = instr_jmp

    def _convert_instr(self):

        if self.as_file:
            self._insert_new_file()

        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    # check ingame
                    Instr(PyOps.LOAD_FAST, self.get_is_ingame_var(self._brk_level)),
            jmp1 := Instr(PyOps.POP_JUMP_IF_TRUE, ),

                    # exit to out loop
                    Instr(PyOps.LOAD_FAST, self.get_is_ingame_var(self._brk_level)),
            jmp2 := Instr(PyOps.POP_JUMP_IF_TRUE, ),
                    Instr(PyOps.LOAD_FAST, self.get_loop_file(self._brk_level)),
                    Instr(PyOps.CALL_FUNCTION, 1),
                    Instr(PyOps.POP_TOP),
                    self.instr_jmp,

                    # ingame codes
            tag2 := Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_set_score(self.on_break(self._brk_level), self._brk_level))),
                    Instr(PyOps.CALL_FUNCTION, 1),
                    Instr(PyOps.POP_TOP),
                )),
                0, end=-1, no_convert=True, as_file=False, dbg_name="break"
            )
        )
        jmp2.set_jmp_targ(tag2)

        if self.as_file:
            self._insert_exit_file()
            jmp1.set_jmp_targ(self.last)
        else:
            jmp1.set_jmp_targ(self.next)


class CodeContinue(AbstractCodeBlock):
    """
    continue

    break level: CONTINUE
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_jmp: Instr, reader: ListReader[Instr], offset: int, end: int = -1,
                 as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 2, as_file=as_file, dbg_name=dbg_name)

        assert instr_jmp.op in JMP_ALWAYS

        self._brk_level = breaklevel.CONTINUE

        self.instr_jmp = instr_jmp

    def _convert_instr(self):

        if self.as_file:
            self._insert_new_file()

        self.add_final_sub_and_convert(
            CodeChain(
                self.pyc,
                ListReader((
                    # ingame codes
                    Instr(PyOps.LOAD_GLOBAL,
                          self.pyc.add_name(gen_set_score(self.on_break(self._brk_level), self._brk_level))),
                    Instr(PyOps.CALL_FUNCTION, 1),
                    Instr(PyOps.POP_TOP),

                    self.instr_jmp
                )),
                0, end=-1, no_convert=True, as_file=False, dbg_name="continue"
            )
        )

        if self.as_file:
            self._insert_exit_file()


class CodeReturn(AbstractCodeBlock):
    """
    return ...

    break level: RETURN
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_ret: Instr, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 2, as_file=as_file, dbg_name=dbg_name)

        assert instr_ret.op is PyOps.RETURN_VALUE

        self._brk_level = breaklevel.RETURN

        self.instr_ret = instr_ret

    def _convert_instr(self):

        if self.as_file:
            self._insert_new_file()

        block_ret = CodeChain(
            self.pyc,
            ListReader((
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(convert_return)),
                Instr(PyOps.ROT_TWO),
                Instr(PyOps.CALL_FUNCTION, 1),
                Instr(PyOps.POP_TOP),
                Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(gen_set_score(self.on_break(self._brk_level), self._brk_level))),
                Instr(PyOps.CALL_FUNCTION, 0),
                Instr(PyOps.POP_TOP),
            )),
            self.offset, end=-1, no_convert=True, as_file=False, dbg_name="return"
        )
        self.add_final_sub_and_convert(block_ret)

        if self.as_file:
            self._insert_exit_file()

        for jf in self.instr_ret.jmp_froms:
            jf.set_jmp_targ(block_ret)


class CodeRaise(AbstractCodeBlock):
    """
    raise ... | assert ...

    break level: RETURN
    """

    def __init__(self, pyc: CodeTypeRewriter, instr_raise: Instr, reader: ListReader[Instr], offset: int, end: int = -1, as_file: bool = True, dbg_name=None):
        super().__init__(pyc, reader, offset, end, 2, as_file=as_file, dbg_name=dbg_name)

        assert instr_raise.op is PyOps.RAISE_VARARGS

        self._brk_level = breaklevel.RETURN

        self.instr_raise = instr_raise

    def _convert_instr(self):

        if self.as_file:
            self._insert_new_file()

        instrs_raise = [Instr(PyOps.POP_TOP) for _ in range(self.instr_raise.arg)]  # pop exception objects
        instrs_raise.extend((
            Instr(PyOps.LOAD_GLOBAL,
                  self.pyc.add_name(gen_set_score(self.on_break(self._brk_level), self._brk_level))),
            Instr(PyOps.CALL_FUNCTION, 0),
            Instr(PyOps.POP_TOP),
        ))
        block_raise = CodeChain(
            self.pyc,
            ListReader(instrs_raise),
            self.offset, end=-1, no_convert=True, as_file=False, dbg_name="raise"
        )
        self.add_final_sub_and_convert(block_raise)

        if self.as_file:
            self._insert_exit_file()

        for jf in self.instr_raise.jmp_froms:
            jf.set_jmp_targ(block_raise)


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


def new_brk() -> Score:
    return Score(entity=ScoreEntity.new_dummy("brkflg"))
