from typing import List

from pymcf.operations import Operation
from pymcf.project import Project
from pymcf import logger


class MCFContext:

    _current = None
    _ctx_init_scb = None
    _ctx_init_score = None

    def __init__(self, name: str):
        from pymcf.project import Project
        self.name = name
        self.nfiles = 0
        self.finished = []
        self.file_stack = []
        self.proj: Project = Project.INSTANCE
        self.proj.add_ctx(self)

        self.last = None

    def __enter__(self):
        self.last = MCFContext._current
        MCFContext._current = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        MCFContext._current = self.last

    @staticmethod
    def new_file():
        curr = MCFContext._current
        name = curr.name if curr.nfiles == 0 else curr.name + '_' + str(curr.nfiles)
        curr.file_stack.append(MCFFile(name))
        logger.debug(f"> {name} started.")
        curr.nfiles += 1

    @staticmethod
    def finish_file():
        curr = MCFContext._current
        logger.debug(f"< {curr.top.name} finished.")
        curr.top.finish()
        curr.finished.append(curr.file_stack.pop())

    # noinspection PyMethodParameters
    @staticmethod
    def last_finished():
        curr = MCFContext._current
        return curr.finished[-1]

    # noinspection PyMethodParameters
    @property
    def top(self):
        assert len(self.file_stack) > 0
        return self.file_stack[-1]

    @staticmethod
    def append_op(op: Operation):
        """
        append one operation to current file of current context
        :param op: mcfunction operation
        """
        MCFContext._current.top.append_op(op)
        logger.debug(f"    + {MCFContext._current.top.name}: {op}")

    @staticmethod
    def INIT_SCB():
        if MCFContext._ctx_init_scb is None:
            MCFContext._ctx_init_scb = MCFContext("sys.init_scoreboard")
        return MCFContext._ctx_init_scb

    @staticmethod
    def INIT_SCORE():
        if MCFContext._ctx_init_score is None:
            MCFContext._ctx_init_score = MCFContext("sys.init_score")
        return MCFContext._ctx_init_score


class MCFFile:

    def __init__(self, name: str):
        self.name = name
        self.proj: Project = Project.INSTANCE
        self.operations: List[Operation] = []

    def append_op(self, op: Operation):
        self.operations.append(op)

    def finish(self):
        self.gen()

    def gen(self):
        with open(self.proj.output_dir + self.name + ".mcfunction", 'w') as f:
            for op in self.operations:
                f.write(op.gen_code(self.proj.mc_version) + '\n')
