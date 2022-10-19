from typing import List, Any

from pymcf.operations import Operation
from pymcf.project import Project
from pymcf import logger
from util import staticproperty


class MCFContext:
    _current = None
    _ctx_init_scb = None
    _ctx_init_score = None

    def __init__(self, name: str, generator=None):
        from pymcf.project import Project
        self.name = name
        self.generator = generator
        self.nfiles = 0
        self.files = []
        self.file_stack = []
        self.return_value = None
        self.proj: Project = Project.INSTANCE
        self.proj.add_ctx(self)

        self.last = None

    def __enter__(self):
        logger.info(f">> compiling context: {self.name}")
        self.last = MCFContext._current
        MCFContext._current = self
        MCFContext.new_or_last()  # if main file of this context exists, load it

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_file()
        if len(self.file_stack) > 0:
            logger.warning(f"{len(self.file_stack)} files remaining: {self.file_stack}")
        logger.info(f"<< exit context: {self.name}")
        MCFContext._current = self.last

    # noinspection PyMethodParameters
    @staticproperty
    def in_context() -> bool:
        return MCFContext._current is not None

    def gen_files(self):
        for mcf_file in self.files:
            mcf_file.gen()

    @staticmethod
    def new_or_last():
        curr = MCFContext._current
        if len(curr.files) > 0:
            curr.file_stack.append(curr.files.pop())
            logger.info(f" > reopen file: {MCFContext.current_file().name}")
        else:
            MCFContext.new_file()

    @staticmethod
    def new_file():
        curr = MCFContext._current
        name = curr.name if curr.nfiles == 0 else curr.name + '_' + str(curr.nfiles)
        logger.info(f" > collecting file: {name}")
        curr.file_stack.append(MCFFile(name))
        curr.nfiles += 1

    @staticmethod
    def exit_file():
        curr = MCFContext._current
        logger.info(f" < exit file: {MCFContext.current_file().name}")
        curr.files.append(curr.file_stack.pop())

    @staticmethod
    def last_file():
        curr = MCFContext._current
        return curr.files[-1]

    @staticmethod
    def current_file():
        curr = MCFContext._current
        assert len(curr.file_stack) > 0
        return curr.file_stack[-1]

    @staticmethod
    def append_op(op: Operation):
        """
        append one operation to current file of current context
        :param op: mcfunction operation
        """
        MCFContext.current_file().append_op(op)
        logger.debug(f"    + {MCFContext.current_file().name}: {op}")

    @staticmethod
    def assign_return_value(value: Any):  # TODO
        curr: MCFContext = MCFContext._current
        if curr.return_value is None:
            curr.return_value = value
            logger.debug(f"    * return value accepted: {value}")
        elif curr.return_value != value:
            logger.error("return value error.")

    @staticmethod
    def get_return_value():
        curr: MCFContext = MCFContext._current
        return curr.return_value

    def post_process(self):  # TODO build function call graph, check data overwriting, and optimize
        # logger.info(f"== post processing context: {self.name}")
        pass

    # noinspection PyMethodParameters
    @staticproperty
    def INIT_SCB():
        if MCFContext._ctx_init_scb is None:
            MCFContext._ctx_init_scb = MCFContext("sys.init_scoreboard")
        return MCFContext._ctx_init_scb

    # noinspection PyMethodParameters
    @staticproperty
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

    def gen(self):
        logger.info(f"generating file: {self.name}")
        with open(self.proj.output_dir + self.name + ".mcfunction", 'w') as f:
            for op in self.operations:
                f.write(op.gen_code(self.proj.mc_version) + '\n')

    def __repr__(self):
        return f"MCFFile: {self.name}"
