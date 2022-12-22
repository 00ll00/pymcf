from typing import List, Any, Set, Optional, Dict

from pymcf._project import Project
from pymcf import logger
from pymcf.util import staticproperty, lazy, create_file_dir


class MCFContext:
    """
    MC Function Context

    a MCFContext represents a mcfunction with a set of parameters.
    context hold arg variables, arg tags, and record the return value of decorated python function.
    it could contain multiple MCFFiles, this files share same context, but can have different executor.
    """

    _current: "MCFContext" = None  # see MCFContext.current()

    def __init__(self, name: str, func_tags: Optional[Set[str]] = None, is_entry_point: bool = False, executor=None):
        from pymcf._project import Project
        self.name = name
        self.func_tags = func_tags if func_tags is not None else set()
        self.ep = is_entry_point
        self.nfiles = 0  # see new_file()
        self.files: List[MCFFile] = []  # MCFFiles finished
        self.file_stack = []  # MCFFiles still collecting
        self.return_value = None  # return value for wrapped python function. see
        self.proj = Project
        self.proj.add_ctx(self)
        self.executor = executor

        self.last_ctx = None

    def __enter__(self):
        """
        open base file while entering context.
        """
        logger.debug(f">> compiling context: {self.name}")

        if len(self.files) > 0:
            self.file_stack.append(self.files.pop())
            logger.debug(f" > reopen file: {self.file_stack[-1].name}")
        else:
            MCFContext.new_file(self, executor=self.executor)
        self.last_ctx = MCFContext._current
        MCFContext._current = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            logger.error(f"unhandled exception occurred while processing file '{MCFContext.last_file().name}':"
                         f"    {exc_type.__qualname__}: {exc_val}")
        if len(self.file_stack) > 1:
            logger.warning(f"{len(self.file_stack)} files remaining: {self.file_stack}")
        else:
            MCFContext.exit_file()
        logger.debug(f"<< exit context: {self.name}")
        MCFContext._current = self.last_ctx

    # noinspection PyMethodParameters
    @staticproperty
    def current() -> Optional["MCFContext"]:
        return MCFContext._current

    # noinspection PyMethodParameters
    @staticproperty
    def in_context() -> bool:
        return MCFContext.current is not None and len(MCFContext.current.file_stack) > 0

    @staticmethod
    def current_return_value():
        return MCFContext.current.return_value

    @staticmethod
    def current_executor():
        if MCFContext.in_context:
            return MCFContext.current_file().executor
        else:
            return None

    def gen_files(self):
        for mcf_file in self.files:
            mcf_file.gen()

    @staticmethod
    def new_file(ctx=None, executor=None):
        """
        open a new file in current context, or specified context if given.
        """
        curr = MCFContext.current if ctx is None else ctx
        name = curr.name if curr.nfiles == 0 else curr.name + '.' + str(curr.nfiles)
        if len(curr.file_stack) > 0 and executor is None:
            executor = curr.file_stack[-1].executor
        logger.debug(f" > collecting file: {name}, with executor: {executor}")
        curr.file_stack.append(MCFFile(name, curr.nfiles == 0, executor=executor))
        curr.nfiles += 1

    @staticmethod
    def exit_file():
        """
        finish current file.
        """
        curr = MCFContext.current
        file = curr.file_stack[-1]
        for entity in file.arg_entity:
            from pymcf.operations.entity_ops import DelTagOp
            DelTagOp(entity, entity.id_tag)
        curr.file_stack.pop()
        logger.debug(f" < exit file: {file.name}")
        curr.files.append(file)

    @staticmethod
    def last_file() -> "MCFFile":
        curr = MCFContext.current
        return curr.files[-1]

    @staticmethod
    def current_file() -> "MCFFile":
        curr = MCFContext.current
        assert len(curr.file_stack) > 0
        return curr.file_stack[-1]

    @staticmethod
    def outer_file() -> "MCFFile":
        curr = MCFContext.current
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
        curr: MCFContext = MCFContext.current
        if curr.return_value is None:
            curr.return_value = value
            logger.debug(f"    * return value accepted: {value}")
        elif curr.return_value != value:
            logger.error("return value error.")

    @staticmethod
    def get_return_value():
        curr: MCFContext = MCFContext.current
        return curr.return_value

    @staticmethod
    def assign_arg_entity(entity):
        """
        assign an arg entity to current mcfunction file.
        id_tag of arg entity will be removed while exit file.
        """
        MCFContext.current.current_file().arg_entity.append(entity)

    def post_process(self):  # TODO build function call graph, check data overwriting, and optimize
        # logger.info(f"== post processing context: {self.name}")
        pass

    # noinspection PyMethodParameters
    @staticproperty
    @lazy
    def INIT_STORE():
        """
        init data storage (and scoreboard objective).
        """
        return MCFContext("sys.init_store", func_tags={"load"}, is_entry_point=True)

    # noinspection PyMethodParameters
    @staticproperty
    @lazy
    def INIT_VALUE():
        """
        init values (constant, nbt structure ...).
        """
        return MCFContext("sys.init_value", func_tags={"load"}, is_entry_point=True)


class MCFFile:
    """
    MC Function File

    each MCFFile associated to a '.mcfunction' file.
    MCFFile records operations, witch generate mcfunction command text finally.
    """

    def __init__(self, name: str, is_entry_point: bool = False, executor=None):
        self.ep = is_entry_point
        self.name = name
        self.proj = Project
        self.operations: List = []
        self.executor = executor
        self.arg_entity = []

        self._calls: Dict = {}
        self._callers: Dict = {}

    def append_op(self, op):
        self.operations.append(op)

    def gen(self):
        logger.info(f"generating file: {self.name}")
        file = self.proj.output_dir + self.name + ".mcfunction"
        create_file_dir(file)
        with open(file, 'w') as f:
            for op in self.operations:
                f.write(op.gen_code(self.proj.mc_version) + '\n')

    def __repr__(self):
        return f"MCFFile: {self.name}"
