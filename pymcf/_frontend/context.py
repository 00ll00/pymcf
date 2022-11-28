from typing import List, Any, Set, Optional, Dict

from pymcf.project import Project
from pymcf import logger
from pymcf.util import staticproperty, lazy


class MCFContext:
    _current: "MCFContext" = None
    _ctx_init_scb = None
    _ctx_init_score = None

    _total_entity_tag_num = 0

    def __init__(self, name: str, tags: Optional[Set[str]] = None, is_enter_point: bool = False, single_file: bool = False):
        from pymcf.project import Project
        self.name = name
        self.tags = tags if tags is not None else set()
        self.ep = is_enter_point
        self.sf = single_file
        self.nfiles = 0
        self.files: List[MCFFile] = []
        self.file_stack = []
        self.return_value = None
        self.proj: Project = Project.INSTANCE
        self.proj.add_ctx(self)

        self.entity_tags = []

        self.last = None

    def __enter__(self):
        logger.debug(f">> compiling context: {self.name}")
        if len(self.file_stack) == 0 and self.sf:
            self._new_or_last_file()
        self.last = MCFContext._current
        MCFContext._current = self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if len(self.file_stack) > 0:
            if self.sf:
                self.exit_file()
            else:
                logger.warning(f"{len(self.file_stack)} files remaining: {self.file_stack}")
        logger.debug(f"<< exit context: {self.name}")
        MCFContext._current = self.last

    # noinspection PyMethodParameters
    @staticproperty
    def in_context() -> bool:
        return MCFContext._current is not None

    def gen_files(self):
        for mcf_file in self.files:
            mcf_file.gen()

    def _new_or_last_file(self):
        if len(self.files) > 0:
            self.file_stack.append(self.files.pop())
            logger.debug(f" > reopen file: {self.file_stack[-1].name}")
        else:
            MCFContext.new_file(self)

    @staticmethod
    def new_file(ctx=None):
        curr = MCFContext._current if ctx is None else ctx
        name = curr.name if curr.nfiles == 0 else curr.name + '_' + str(curr.nfiles)
        logger.debug(f" > collecting file: {name}")
        curr.file_stack.append(MCFFile(name, curr.nfiles == 0))
        curr.nfiles += 1

    @staticmethod
    def exit_file():
        curr = MCFContext._current
        file = curr.file_stack.pop()
        logger.debug(f" < exit file: {file.name}")
        curr.files.append(file)

    @staticmethod
    def last_file() -> "MCFFile":
        curr = MCFContext._current
        return curr.files[-1]

    @staticmethod
    def current_file() -> "MCFFile":
        curr = MCFContext._current
        assert len(curr.file_stack) > 0
        return curr.file_stack[-1]

    @staticmethod
    def outer_file() -> "MCFFile":
        curr = MCFContext._current
        assert len(curr.file_stack) > 1
        return curr.file_stack[-2]

    @staticmethod
    def append_op(op):
        """
        append one operation to current file of current context
        :param op: mcfunction operation
        """
        MCFContext.current_file().append_op(op)
        logger.debug(f"    + {MCFContext.current_file().name}: {op}")

    @staticmethod
    def assign_return_value(value: Any):  # TODO check value structure same
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

    @staticmethod
    def new_entity_tag() -> str:
        MCFContext._total_entity_tag_num += 1
        tag = f"{Project.namespace}.tag_{MCFContext._total_entity_tag_num}"
        MCFContext._current.entity_tags.append(tag)
        return tag

    def post_process(self):  # TODO build function call graph, check data overwriting, and optimize
        # logger.info(f"== post processing context: {self.name}")
        pass

    # noinspection PyMethodParameters
    @staticproperty
    @lazy
    def INIT_STORE():
        return MCFContext("sys.init_store", tags={"load"}, is_enter_point=True, single_file=True)

    # noinspection PyMethodParameters
    @staticproperty
    @lazy
    def INIT_VALUE():
        return MCFContext("sys.init_value", tags={"load"}, is_enter_point=True, single_file=True)


class MCFFile:

    def __init__(self, name: str, is_entry_point: bool = False):
        self.ep = is_entry_point
        self.name = name
        self.proj: Project = Project.INSTANCE
        self.operations: List = []

        self._calls: Dict = {}
        self._callers: Dict = {}

    def append_op(self, op):
        self.operations.append(op)

    def gen(self):
        logger.info(f"generating file: {self.name}")
        with open(self.proj.output_dir + self.name + ".mcfunction", 'w') as f:
            for op in self.operations:
                f.write(op.gen_code(self.proj.mc_version) + '\n')

    def __repr__(self):
        return f"MCFFile: {self.name}"
