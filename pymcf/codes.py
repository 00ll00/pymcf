import dis
from dis import Instruction
from enum import Enum
from types import FunctionType, CodeType
from typing import List, Optional, Dict, Iterator, Any, Tuple

from pymcf.code_helpers import convert_assign, finish_file
from pymcf.operations import raw
from pymcf.pyops import PyOps, JMP, JABS


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

        cl = CodeLogic(self, dis.Bytecode(ct).__iter__())
        code, lnotab, stack_size = cl.gen_code()

        self.codetype: CodeType = CodeType(
            self.co_argcount,
            self.co_posonlyargcount,
            self.co_kwonlyargcount,
            len(self.co_varnames),
            ct.co_stacksize + 5,  # TODO
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

    @staticmethod
    def _get_name(obj: object):
        return "<obj_" + str(id(obj)) + ">"

    def add_name(self, obj: Any, name: str = None) -> int:
        if name is None:
            name = self._get_name(obj)
        if name not in self.co_names:
            self.co_names.append(name)
            self.globals[name] = obj
        return self.co_names.index(name)

    def add_const(self, obj: Any) -> int:
        if obj not in self.co_consts:
            self.co_consts.append(obj)
        return self.co_consts.index(obj)


class Instr:

    def __init__(self, op: PyOps, arg: int = 0, line_code: Optional[int] = None, arg_rel_pos: Optional[int] = None):
        self.op = op
        self.arg = arg
        self.offset = 0
        self.line_code = line_code
        self.arg_rel_pos = arg_rel_pos

    @staticmethod
    def wrap(instr: Instruction):
        return Instr(PyOps(instr.opcode), instr.arg if instr.arg is not None else 0, instr.starts_line)

    @property
    def opcode(self) -> int:
        return self.op.value

    @property
    def opname(self) -> str:
        return self.op.name

    def __repr__(self):
        return f"Instr: {self.op.name}, {self.arg}"


class CodeBlock:

    def __init__(self, pyc: PyCode, offset: int):
        self.pyc: PyCode = pyc
        self.offset: int = offset
        self.jmp_target: Optional[CodeBlock] = None
        self.next: Optional[CodeBlock] = None

    @property
    def size(self) -> int:
        """
        byte size of this block
        """
        raise NotImplementedError()

    def _convert_instr(self):
        raise NotImplementedError()

    def _reset_jmp_pos(self):
        raise NotImplementedError()

    def _get_instrs(self) -> List[Instr]:
        raise NotImplementedError()


class CodeLogic(CodeBlock):

    def __init__(self, pyc: PyCode, instr_iter: Iterator[Instruction], end: Optional[int] = None):
        super().__init__(pyc, None)
        self.cbs: Dict[int, CodeBlock] = {}
        self.current: Optional[CodeChain] = None

        for instr in instr_iter:
            my_instr = Instr.wrap(instr)
            offset = instr.offset
            if offset == end:
                break
            if self.offset is None:
                self.offset = offset
                self.new_chain(offset)

            if instr.is_jump_target:
                if offset != self.current.offset:
                    self.new_chain(offset)

            match my_instr.op:
                case PyOps.FOR_ITER:  # pack for_iter
                    self.current.set_for_instr(my_instr)
                    for_end = instr.argval
                    self.new_chain(for_end)
                case PyOps.RETURN_VALUE:
                    self.current.set_ret_instr(my_instr)
                    self.new_chain(offset + 2)
                case op if op in JMP:
                    pos = instr.argval if op in JABS else instr.offset + instr.argval
                    self.current.set_jmp_instr(my_instr, pos)
                    self.new_chain(offset + 2)
                case _:
                    self.current.add_instr(my_instr)

        if self.current.size > 0:
            self.cbs[self.current.offset] = self.current

        # link code blocks
        lcb = None
        for i in sorted(self.cbs):
            cb = self.cbs[i]
            if lcb is not None:
                lcb.next = cb
            if isinstance(cb, CodeChain):
                if cb.jmp_pos is not None:
                    cb.jmp_target = self.cbs[cb.jmp_pos]
            lcb = cb

        # compute code block offset
        offset = self.offset
        for i in sorted(self.cbs):
            cb = self.cbs[i]
            cb.offset = offset
            offset += cb.size

    def new_chain(self, offset: int):
        if self.current is not None:
            self.cbs[self.current.offset] = self.current
        self.current = CodeChain(self.pyc, offset)

    def _convert_instr(self):
        offset = self.offset
        for i in sorted(self.cbs):
            cb = self.cbs[i]
            cb.offset = offset
            cb._convert_instr()
            offset += cb.size

    def _reset_jmp_pos(self):

        for cb in self.cbs.values():
            cb._reset_jmp_pos()

    def _get_instrs(self) -> List[Instr]:
        res = []
        for i in sorted(self.cbs):
            cb = self.cbs[i]
            res.extend(cb._get_instrs())
        return res

    def gen_code(self) -> Tuple[bytes, bytes, int]:
        self._convert_instr()
        self._reset_jmp_pos()
        max_stack = 0
        code = bytearray()
        lnotab = bytearray()
        last_line = self.pyc.co_firstlineno
        last_offset = self.offset
        for instr in self._get_instrs():
            if instr.line_code is not None:
                lnotab.append(instr.offset - last_offset)
                lnotab.append(instr.line_code - last_line)
                last_offset = instr.offset
                last_line = instr.line_code
            code.append(instr.opcode)
            code.append(instr.arg)
            max_stack += dis.stack_effect(instr.opcode, instr.arg if instr.opcode >= dis.HAVE_ARGUMENT else None,
                                          jump=True)
        return bytes(code), bytes(lnotab), max_stack

    @property
    def size(self) -> int:
        return sum(sub.size for sub in self.cbs.values()) if len(self.cbs) > 0 else 0

    def __repr__(self):
        return f"CodeChain: offset: {self.offset} size: {self.cbs}"


class CodeChain(CodeBlock):

    def __init__(self, pyc: PyCode, offset: int):
        super().__init__(pyc, offset)
        self.instructions: List[Instr] = []
        self.final_instr: Optional[Instr] = None
        self.jmp_instr: Optional[Instr] = None
        self.jmp_pos: Optional[int] = None
        self.is_end: bool = False

    def add_instr(self, instr: Instr):
        self.instructions.append(instr)

    def set_for_instr(self, instr: Instr):
        assert instr.op is PyOps.FOR_ITER
        self.final_instr = instr

    def set_jmp_instr(self, instr: Instr, jmp_pos: int):
        assert instr.op in JMP
        self.final_instr = instr
        self.jmp_pos = jmp_pos

    def set_ret_instr(self, instr: Instr):
        assert instr.op is PyOps.RETURN_VALUE
        self.final_instr = instr
        self.is_end = True

    def _convert_instr(self):
        i = 0
        while i < len(self.instructions):
            curr = self.instructions[i]
            last = None if i == 0 else self.instructions[i - 1]

            # (BUILD_STRING | LOAD_CONST) POP_TOP
            # convert lonely formatted string to mcfunction part
            if curr.op is PyOps.POP_TOP and last is not None and last.op in {PyOps.BUILD_STRING, PyOps.LOAD_CONST}:
                self.instructions.insert(i, Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(raw)))
                self.instructions.insert(i + 1, Instr(PyOps.ROT_TWO))
                self.instructions.insert(i + 2, Instr(PyOps.CALL_FUNCTION, 1))
                i += 4
                continue

            # STORE_FAST | STORE_ATTR | STORE_NAME | STORE_GLOBAL | STORE_DEREF
            #  direct Score assignment (e.g. a = 1)
            if curr.op in {PyOps.STORE_FAST, PyOps.STORE_ATTR, PyOps.STORE_NAME, PyOps.STORE_GLOBAL, PyOps.STORE_DEREF}:
                match curr.op:
                    case PyOps.STORE_FAST:
                        self.instructions.insert(i, Instr(PyOps.LOAD_CONST,
                                                          self.pyc.add_const(self.pyc.co_varnames[curr.arg])))
                        self.instructions.insert(i + 1, Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(locals, "locals")))
                        self.instructions.insert(i + 2, Instr(PyOps.CALL_FUNCTION, 0))
                        self.instructions.insert(i + 3, Instr(PyOps.CONTAINS_OP, 0))
                        self.instructions.insert(i + 4, Instr(PyOps.POP_JUMP_IF_FALSE, arg_rel_pos=10))
                        self.instructions.insert(i + 5, Instr(PyOps.LOAD_FAST, curr.arg))
                        self.instructions.insert(i + 6, Instr(PyOps.LOAD_NAME, self.pyc.add_name(convert_assign)))
                        self.instructions.insert(i + 7, Instr(PyOps.ROT_THREE))
                        self.instructions.insert(i + 8, Instr(PyOps.CALL_FUNCTION, 2))
                    case PyOps.STORE_GLOBAL:
                        self.instructions.insert(i, Instr(PyOps.LOAD_GLOBAL, curr.arg))
                        self.instructions.insert(i + 1, Instr(PyOps.LOAD_NAME, self.pyc.add_name(convert_assign)))
                        self.instructions.insert(i + 2, Instr(PyOps.ROT_THREE))
                        self.instructions.insert(i + 3, Instr(PyOps.CALL_FUNCTION, 2))
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

        if self.final_instr is not None:
            match self.final_instr.op:
                case PyOps.RETURN_VALUE:
                    self.instructions.append(Instr(PyOps.LOAD_GLOBAL, self.pyc.add_name(finish_file)))
                    self.instructions.append(Instr(PyOps.CALL_FUNCTION, 0))
                    self.instructions.append(self.final_instr)  # TODO

        for i, instr in enumerate(self.instructions):
            instr.offset = self.offset + 2 * i
            if instr.arg_rel_pos is not None:
                instr.arg = (instr.offset + instr.arg_rel_pos) // 2

    def _reset_jmp_pos(self):
        if self.jmp_instr is not None:
            self.jmp_instr.arg = self.jmp_target.offset

    def _get_instrs(self) -> List[Instr]:
        return self.instructions.copy()

    @property
    def size(self) -> int:
        return 2 * len(self.instructions)

    def __repr__(self):
        return f"CodeBlock: offset: {self.offset}, size: {self.size}, jmp: {self.jmp_pos}"


class CodeIfElse(CodeBlock):

    def __init__(self, pyc: PyCode, offset: int):
        super().__init__(pyc, offset)

    def _convert_instr(self):
        pass

    def _reset_jmp_pos(self):
        pass

    def _get_instrs(self) -> List[Instr]:
        pass

    @property
    def size(self) -> int:
        pass
