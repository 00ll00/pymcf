import inspect
from _ast import If, IfExp, FunctionDef, Call, Name, expr, Load, Assign, Store, stmt, arguments, Pass, With, \
    withitem, Constant, Or, BoolOp, Attribute, Nonlocal, Return, AnnAssign, Compare, And, NamedExpr, Assert, boolop, \
    Not, FormattedValue, UnaryOp, While, Continue, Break, For, Expr
from abc import ABC
from ast import parse as parse_ast, AST, NodeTransformer, fix_missing_locations
from types import FunctionType, CodeType
from typing import Any, Dict, Tuple, Set, final, List

from .context import MCFContext
from .ct_rewrite import CodeTypeRewriter
from pymcf.data import InGameData, InGameIterator, InGameObj, Score, ScoreDummy, Scoreboard
from pymcf.operations import CallFunctionOp, ExecuteOp, IfScoreLTValueRunOp, IfScoreGEValueRunOp
from .break_level import BreakLevel


def _wrapped_and(left, right):
    if isinstance(left, InGameData):
        return left.__bool_and__(right)
    elif isinstance(right, InGameData):
        return right.__bool_and__(left)
    else:
        return left and right


def _wrapped_or(left, right):
    if isinstance(left, InGameData):
        return left.__bool_or__(right)
    elif isinstance(right, InGameData):
        return right.__bool_or__(left)
    else:
        return left or right


def _wrapped_not(value):
    if isinstance(value, InGameData):
        return value.__bool_not__()
    else:
        return not value


class CtxManager(ABC):
    _current: "CtxManager" = None
    __brkflg_count = 0

    @staticmethod
    @final
    def _send_break(flag: Score, level: int):
        flag.set_value(level)

    def __init__(self):
        self.parent: "CtxManager"
        self.brk_flags: Set[Score] = set()

    @staticmethod
    @final
    def new_break() -> Score:
        CtxManager.__brkflg_count += 1
        flag_name = f"$bf_{CtxManager.__brkflg_count}"
        return Score(entity=ScoreDummy(flag_name), objective=Scoreboard.SYS)

    @staticmethod
    @final
    def send_break(brk_lvl: BreakLevel | int):
        brk_lvl = BreakLevel.from_value(brk_lvl)
        brk_flag = CtxManager._current.receive_break(brk_lvl)
        brk_flag.set_value(brk_lvl)

    def __enter__(self):
        self.parent = CtxManager._current
        CtxManager._current = self
        MCFContext.new_file()

    def __exit__(self, exc_type, exc_val, exc_tb):
        CtxManager._current = self.parent
        MCFContext.exit_file()
        self.after_exit()

    def after_exit(self):
        run = CallFunctionOp(MCFContext.last_file().name, offline=True)
        for flag in self.brk_flags:
            run = IfScoreLTValueRunOp(flag, 1, run, offline=True)
        ExecuteOp(run)

    def receive_break(self, brk_lvl: BreakLevel) -> Score:
        brk_flag = self.parent.receive_break(brk_lvl)
        self.brk_flags.add(brk_flag)
        return brk_flag


class DummyCtxManager(CtxManager):

    def __enter__(self):
        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def after_exit(self):
        return

    def receive_break(self, brk_lvl: BreakLevel) -> Score:
        return self.parent.receive_break(brk_lvl)


class BranchCtxManager(CtxManager):
    """
    manage branch statement like `if ... else ...`.
    only check condition, and decide with branch to run.
    check condition is `cond_var >= cmp_value`.
    """

    def __init__(self, is_ingame: bool, cond_var: Score, on_true: bool, cmp_value: int = 1):
        super().__init__()
        self.is_ingame = is_ingame
        self.cond_var = cond_var
        self.on_true = on_true
        self.cmp_value = cmp_value

    def __enter__(self):
        if self.is_ingame:
            super(BranchCtxManager, self).__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_ingame:
            super(BranchCtxManager, self).__exit__(exc_type, exc_val, exc_tb)

    def receive_break(self, brk_lvl: BreakLevel) -> Score:
        # don't record any break
        return self.parent.receive_break(brk_lvl)

    def after_exit(self):
        run_op = IfScoreGEValueRunOp if self.on_true else IfScoreLTValueRunOp
        run_op(self.cond_var, self.cmp_value, CallFunctionOp(MCFContext.last_file().name, offline=True))


class LoopCtxManager(CtxManager):
    """
    manage loops
    """

    def __init__(self):
        super().__init__()
        self.brk_flag = self.new_break()
        self.ingame: bool = False

    @staticmethod
    @final
    def is_last_loop_ingame() -> bool:
        ctx = CtxManager._current
        while not isinstance(ctx, LoopCtxManager):
            ctx = ctx.parent
        return ctx.ingame

    @staticmethod
    @final
    def get_last_brk_flg() -> Score:
        ctx = CtxManager._current
        while not isinstance(ctx, LoopCtxManager):
            ctx = ctx.parent
        return ctx.brk_flag

    @staticmethod
    @final
    def set_loop_ingame(ingame: bool):
        ctx = CtxManager._current
        while not isinstance(ctx, LoopCtxManager):
            ctx = ctx.parent
        ctx.ingame = ingame

    def receive_break(self, brk_lvl: BreakLevel):
        if brk_lvl >= BreakLevel.RETURN:
            flg = self.parent.receive_break(brk_lvl)
            self.brk_flags.add(flg)
            return flg
        else:
            return self.brk_flag

    def __enter__(self):
        super(LoopCtxManager, self).__enter__()
        self.brk_flag.set_value(BreakLevel.PASS.value)

    def after_exit(self):
        if self.ingame:
            MCFContext.last_file().append_op(
                IfScoreLTValueRunOp(self.brk_flag, BreakLevel.BREAK.value,
                                    CallFunctionOp(MCFContext.current_file().name, offline=True), offline=True)
            )


class FuncCtxManager(LoopCtxManager):
    """
    manage function def
    """

    @staticmethod
    def is_top_level() -> bool:
        ctx = CtxManager._current
        while not isinstance(ctx, FuncCtxManager):
            ctx = ctx.parent
        return ctx._is_top_level

    def __init__(self, top_level: bool = False):
        super().__init__()
        self.brk_flag = self.new_break()
        self.ingame: bool = True
        self._is_top_level = top_level

    def after_exit(self):
        return

    def receive_break(self, brk_lvl: BreakLevel):
        assert brk_lvl >= BreakLevel.RETURN
        return self.brk_flag


class MCFTransformer(NodeTransformer):
    _current: "MCFTransformer"

    def __init__(self, inline: bool = False):
        super(MCFTransformer, self).__init__()
        self._inline = inline
        self._obj_count = 0
        self._glb = {}
        self._helper_funcs = []
        self._helper_vars = []
        self._is_const_loop = []
        self._func_num = 0
        MCFTransformer._current = self

    @staticmethod
    def add_helper_func(func: FunctionDef):
        MCFTransformer._current._helper_funcs.append(func)

    @staticmethod
    def add_helper_var(name: str):
        MCFTransformer._current._helper_vars.append(name)

    @staticmethod
    def new_obj_name() -> str:
        MCFTransformer._current._obj_count += 1
        return f"<obj_{MCFTransformer._current._obj_count}>"

    @staticmethod
    def empty_arg() -> arguments:
        return arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[])

    @staticmethod
    def Const(obj: Any, name: str = None) -> Name:
        curr = MCFTransformer._current
        if name is None:
            if obj in curr._glb.values():
                name = (k for k, v in curr._glb.items() if v is obj).__next__()
            else:
                name = curr.new_obj_name()
                curr._glb[name] = obj
        else:
            assert name not in curr._glb
            curr._glb[name] = obj
        return Name(id=name, ctx=Load())

    def get_globals(self):
        return self._glb

    def IsInGameObjExpr(self, expression: expr) -> Call:
        return Call(
            func=self.Const(isinstance),
            args=[
                expression,
                self.Const(InGameObj)
            ],
            keywords=[]
        )

    def IsInGameDataExpr(self, expression: expr) -> Call:
        return Call(
            func=self.Const(isinstance),
            args=[
                expression,
                self.Const(InGameData)
            ],
            keywords=[]
        )

    def IsInGameIterExpr(self, expression: expr) -> Call:
        return Call(
            func=self.Const(isinstance),
            args=[
                expression,
                self.Const(InGameIterator)
            ],
            keywords=[]
        )

    def _build_raw_assign(self, value: expr, name: str = None) -> Tuple[stmt, str] | stmt:
        """
        name should startswith '<raw>' if given.
        if name is not None, then return value will only have assign statement, else
        return assign statement and new var name.
        """
        if name is None:
            name = "<raw>" + self.new_obj_name()
            return Assign([Name(id=name, ctx=Store())], value=value), name
        else:
            return Assign([Name(id=name, ctx=Store())], value=value)

    def _build_if_stmt(self, test: expr, body: List[stmt], orelse: List[stmt], lineno: int,
                       no_ingame: bool = False) -> stmt:
        # this should not rewrite into function def and call, break / continue statement will be misleading

        has_else = len(orelse) > 0

        # cond var
        assign_cond, name_cond_var = self._build_raw_assign(value=test)

        # assert if ingame var not allowed
        no_ingame_assert = Assert(
            test=self.IsInGameObjExpr(Name(id=name_cond_var, ctx=Load())),
            msg=f"InGameObj is not allowed in condition here. (at line: {lineno})"
        ) if no_ingame else Pass()

        # cond ingame var
        assign_cond_ingame, name_cond_ingame_var = self._build_raw_assign(
            value=self.IsInGameDataExpr(Name(id=name_cond_var, ctx=Load()))
        )
        # cond fail var, use a variable to avoid get conditions value twice
        assign_cond_fail, name_cond_fail_var = self._build_raw_assign(value=Constant(value=False))

        # if true
        if_true = If(
            test=Name(id=name_cond_var, ctx=Load()),
            body=[
                With(
                    items=[
                        withitem(
                            context_expr=Call(
                                func=self.Const(BranchCtxManager),
                                args=[
                                    Name(id=name_cond_ingame_var, ctx=Load()),
                                    Name(id=name_cond_var, ctx=Load()),
                                    Constant(value=True)
                                ],
                                keywords=[]
                            )
                        )
                    ],
                    body=body
                )
            ],
            orelse=[
                self._build_raw_assign(Constant(value=True), name_cond_fail_var)
            ]
        )

        # if false
        if_false = If(
            test=BoolOp(
                op=Or(),
                values=[
                    Name(id=name_cond_fail_var, ctx=Load()),
                    Name(id=name_cond_ingame_var, ctx=Load())
                ]
            ),
            body=[
                With(
                    items=[
                        withitem(
                            context_expr=Call(
                                func=self.Const(BranchCtxManager),
                                args=[
                                    Name(id=name_cond_ingame_var, ctx=Load()),
                                    Name(id=name_cond_var, ctx=Load()),
                                    Constant(value=False)
                                ],
                                keywords=[]
                            )
                        )
                    ],
                    body=orelse
                )
            ],
            orelse=[]
        ) if has_else else Pass()

        new_node = With(
            items=[
                withitem(context_expr=Call(func=self.Const(CtxManager), args=[], keywords=[]))
            ],
            body=[
                assign_cond,
                no_ingame_assert,
                assign_cond_ingame,
                assign_cond_fail,
                if_true,
                if_false
            ],
            lineno=lineno
        )
        return new_node

    def _build_if_expr(self, test: expr, body: expr, orelse: expr, lineno: int, no_ingame: bool = False) -> expr:

        name_res = "<raw>" + self.new_obj_name()

        make_ingame_copy = lambda: If(
            test=self.IsInGameObjExpr(Name(id=name_res, ctx=Load())),
            body=[
                Assign(
                    targets=[Name(id=name_res, ctx=Store())],
                    value=Call(
                        func=Attribute(
                            value=Name(id=name_res, ctx=Load()),
                            attr="_make_copy_",
                            ctx=Load()
                        ),
                        args=[],
                        keywords=[]
                    )
                ),
            ],
            orelse=[]
        )

        new_body = [
            Assign(targets=[Name(id=name_res, ctx=Store())], value=body),
            make_ingame_copy()
        ]

        new_orelse = [
            Assign(targets=[Name(id=name_res, ctx=Store())], value=orelse),
            make_ingame_copy()
        ]

        if_stmt = self._build_if_stmt(test, new_body, new_orelse, lineno, no_ingame)

        helper = FunctionDef(
            name=self.new_obj_name(),
            args=self.empty_arg(),
            body=[
                Nonlocal(names=[name_res]),
                if_stmt,
                Return(value=Name(id=name_res, ctx=Load()))
            ],
            decorator_list=[]
        )

        self.add_helper_func(helper)
        self.add_helper_var(name_res)

        return Call(func=Name(id=helper.name, ctx=Load()), args=[], keywords=[], lineno=lineno)

    def _build_bin_bool_op_expr(self, op: boolop, left: expr, right: expr, lineno: int) -> expr:
        if isinstance(op, And):
            func = _wrapped_and
        else:
            func = _wrapped_or
        return Call(
            func=self.Const(func),
            args=[left, right],
            keywords=[],
            lineno=lineno
        )

    def _build_bool_op_expr(self, op: boolop, values: List[expr], lineno: int) -> expr:
        length = len(values)

        new_node = self._build_bin_bool_op_expr(op, values[0], values[1], lineno)

        i = 2
        while i < length:
            new_node = self._build_bin_bool_op_expr(op, new_node, values[i], lineno)
            i += 1

        return new_node

    def _build_break_stmt(self, brk_lvl: BreakLevel) -> stmt:
        if brk_lvl is BreakLevel.CONTINUE:
            breakop = Continue()
        elif brk_lvl is BreakLevel.BREAK:
            breakop = Break()
        else:
            breakop = Pass()

        return If(
            test=Call(
                func=self.Const(LoopCtxManager.is_last_loop_ingame),
                args=[],
                keywords=[]
            ),
            body=[
                Expr(Call(
                    func=self.Const(CtxManager.send_break),
                    args=[
                        Constant(value=brk_lvl.value)
                    ],
                    keywords=[]
                ))
            ],
            orelse=[
                breakop
            ]
        )

    def visit_If(self, node: If) -> stmt:
        node = self.generic_visit(node)
        if isinstance(node.test, Constant):
            return node
        else:
            return self._build_if_stmt(node.test, node.body, node.orelse, node.lineno)

    def visit_IfExp(self, node: IfExp) -> expr:  # TODO ingame if-expr test may not work as expected
        node = self.generic_visit(node)
        if isinstance(node.test, Constant):
            return node
        else:
            return self._build_if_expr(node.test, node.body, node.orelse, node.lineno, no_ingame=True)

    # def visit_Match(self, node: Match) -> stmt: # TODO match

    def visit_Compare(self, node: Compare) -> expr:
        node = self.generic_visit(node)

        cps = [node.left, *node.comparators]
        length = len(cps)

        if length == 2:  # bin comp
            return node

        values = []
        for i in range(length - 1):
            if i == 0:
                values.append(
                    Compare(
                        left=cps[i],
                        ops=[node.ops[i]],
                        comparators=[
                            NamedExpr(target=Name(id=(name := self.new_obj_name()), ctx=Store()), value=cps[i + 1])
                        ]
                    )
                )
            elif i == length - 2:
                values.append(
                    Compare(
                        left=Name(id=name, ctx=Load()),
                        ops=[node.ops[i]],
                        comparators=[
                            cps[i + 1]
                        ]
                    )
                )
            else:
                values.append(
                    Compare(
                        left=Name(id=name, ctx=Load()),
                        ops=[node.ops[i]],
                        comparators=[
                            NamedExpr(target=Name(id=(name := self.new_obj_name()), ctx=Store()), value=cps[i + 1])
                        ]
                    )
                )

        return self._build_bool_op_expr(op=And(), values=values, lineno=node.lineno)

    def visit_BoolOp(self, node: BoolOp) -> expr:
        # make `__bool_and__` or `__bool_or__` call if contains InGameData
        node = self.generic_visit(node)

        return self._build_bool_op_expr(op=node.op, values=node.values, lineno=node.lineno)

    def visit_UnaryOp(self, node: UnaryOp) -> expr:
        # make `__bool_not__` call if contains InGameData
        node = self.generic_visit(node)
        if isinstance(node.op, Not):
            return Call(
                func=self.Const(_wrapped_not),
                args=[node.operand],
                keywords=[]
            )
        else:
            return node

    def visit_Continue(self, node: Continue) -> stmt:
        # use return to cut remaining statements. return will be removed in code type rewriting.
        return With(
            items=[
                withitem(context_expr=Call(func=self.Const(DummyCtxManager), args=[], keywords=[]))
            ],
            body=[
                self._build_break_stmt(BreakLevel.CONTINUE),
                Return()
            ]
        ) if not self._is_const_loop[-1] else node

    def visit_Break(self, node: Break) -> stmt:
        # use return to cut remaining statements. return will be removed in code type rewriting.
        return With(
            items=[
                withitem(context_expr=Call(func=self.Const(DummyCtxManager), args=[], keywords=[]))
            ],
            body=[
                self._build_break_stmt(BreakLevel.BREAK),
                Return()
            ]
        ) if not self._is_const_loop[-1] else node

    def visit_Return(self, node: Return) -> stmt:
        # return will be removed in code type rewriting.
        node = self.generic_visit(node)

        # if this function is not toplevel function, it should work as inline
        new_node = If(
            test=Call(
                func=self.Const(FuncCtxManager.is_top_level),
                args=[],
                keywords=[]
            ),
            body=[
                With(
                    items=[
                        withitem(context_expr=Call(func=self.Const(DummyCtxManager), args=[], keywords=[]))
                    ],
                    body=[
                        self._build_break_stmt(BreakLevel.RETURN),
                        node
                    ]
                )
            ],
            orelse=[
                node
            ]
        ) if not self._inline else node
        return new_node

    def visit_While(self, node: While) -> stmt:
        lc = isinstance(node.test, Constant)
        self._is_const_loop.append(lc)
        node = self.generic_visit(node)
        self._is_const_loop.pop()
        if lc:
            return node

        test_assign, name_test_var = self._build_raw_assign(node.test)
        ingame_assign, name_ingame_var = self._build_raw_assign(
            self.IsInGameObjExpr(Name(id=name_test_var, ctx=Load()))
        )

        new_node = With(
            items=[
                withitem(context_expr=Call(func=self.Const(LoopCtxManager), args=[], keywords=[]))
            ],
            body=[
                While(
                    test=Constant(value=True),
                    body=[
                        test_assign,
                        ingame_assign,
                        Expr(Call(
                            func=self.Const(LoopCtxManager.set_loop_ingame),
                            args=[Name(id=name_ingame_var, ctx=Load())],
                            keywords=[]
                        )),
                        self._build_if_stmt(
                            test=Name(id=name_test_var, ctx=Load()),
                            body=node.body,
                            orelse=[
                                *node.orelse,
                                self._build_break_stmt(BreakLevel.BREAK)
                            ],
                            lineno=node.lineno
                        ),
                        If(
                            test=Name(id=name_ingame_var, ctx=Load()),
                            body=[
                                Break()
                            ],
                            orelse=[]
                        )
                    ],
                    orelse=[]
                )
            ]
        )
        return new_node

    def visit_For(self, node: For) -> stmt:
        lc = isinstance(node.iter, Constant)
        self._is_const_loop.append(lc)
        node = self.generic_visit(node)
        self._is_const_loop.pop()
        if lc:
            return node

        iter_assign, name_iter_var = self._build_raw_assign(
            Call(
                func=Attribute(value=node.iter, attr="__iter__", ctx=Load()),
                args=[],
                keywords=[]
            )
        )

        new_node = If(
            test=self.IsInGameIterExpr(
                NamedExpr(
                    target=iter_assign.targets[0],
                    value=iter_assign.value
                )
            ),
            body=[
                With(
                    items=[
                        withitem(context_expr=Call(func=self.Const(LoopCtxManager), args=[], keywords=[]))
                    ],
                    body=[
                        While(
                            test=Constant(value=True),
                            body=[
                                Expr(Call(
                                    func=self.Const(LoopCtxManager.set_loop_ingame),
                                    args=[Constant(value=True)],
                                    keywords=[]
                                )),
                                Expr(Call(
                                    func=Attribute(value=node.iter, attr="_iter_init_", ctx=Load()),
                                    args=[],
                                    keywords=[]
                                )),
                                Assign(  # converted assign here
                                    targets=[
                                        node.target
                                    ],
                                    value=Call(
                                        func=Attribute(value=Name(id=name_iter_var, ctx=Load()), attr="_iter_next_",
                                                       ctx=Load()),
                                        args=[
                                            Call(func=self.Const(LoopCtxManager.get_last_brk_flg), args=[], keywords=[])
                                        ],
                                        keywords=[]
                                    )
                                ),
                                With(  # if reach iteration end, run block else
                                    items=[
                                        withitem(
                                            context_expr=Call(
                                                func=self.Const(BranchCtxManager),
                                                args=[
                                                    Constant(value=True),
                                                    Call(func=self.Const(LoopCtxManager.get_last_brk_flg), args=[],
                                                         keywords=[]),
                                                    Constant(value=True),
                                                    Constant(value=BreakLevel.BREAK.value)
                                                ],
                                                keywords=[]
                                            )
                                        )
                                    ],
                                    body=node.orelse
                                ) if len(node.orelse) > 0 else Pass(),
                                With(
                                    items=[
                                        withitem(context_expr=Call(func=self.Const(CtxManager), args=[], keywords=[]))
                                    ],
                                    body=node.body
                                ),
                                Expr(Call(
                                    func=Attribute(value=node.iter, attr="_iter_end_", ctx=Load()),
                                    args=[],
                                    keywords=[]
                                )),
                                Break()
                            ],
                            orelse=[]
                        )
                    ]
                )
            ],
            orelse=[
                With(
                    items=[
                        withitem(context_expr=Call(func=self.Const(LoopCtxManager), args=[], keywords=[]))
                    ],
                    body=[
                        Expr(Call(
                            func=self.Const(LoopCtxManager.set_loop_ingame),
                            args=[Constant(value=False)],
                            keywords=[]
                        )),
                        For(
                            target=node.target,
                            iter=Name(id=name_iter_var, ctx=Load()),
                            body=node.body,
                            orelse=node.orelse
                        )
                    ]
                )
            ]
        )

        return new_node

    def visit_FunctionDef(self, node: FunctionDef) -> Any:
        node = self.generic_visit(node)
        self._func_num += 1
        node.decorator_list.clear()  # TODO remove @mcfunction only
        node.body = [
            With(
                items=[
                    withitem(
                        context_expr=Call(
                            func=self.Const(FuncCtxManager),
                            args=[Constant(self._func_num == 1)],
                            keywords=[]
                        )
                    )
                ],
                body=node.body
            )
        ]
        return node

    def visit_Assign(self, node: Assign) -> Any:
        # assign arrangement implemented in codetype rewriting
        return self.generic_visit(node)

    def visit_NamedExpr(self, node: NamedExpr) -> Any:
        # assign arrangement implemented in codetype rewriting
        return self.generic_visit(node)

    def visit_FormattedValue(self, node: FormattedValue) -> Any:
        # raw mcfunction arrangement implemented in codetype rewriting
        return self.generic_visit(node)

    # def visit_Try(self, node) -> Any:
    #     raise SyntaxError("'try' statement not available in mcfunction.")
    #     ...

    def rebuild(self, ast: AST) -> AST:
        ast = self.visit(ast)
        func_body = ast.body[0].body
        for f in self._helper_funcs:
            func_body.insert(0, f)
        for v in self._helper_vars:
            func_body.insert(0, AnnAssign(target=Name(id=v, ctx=Store()), annotation=Constant(value=""), simple=1))
        if not self._inline:
            func_body.append(
                Return(
                    value=Call(
                        func=self.Const(MCFContext.current_return_value, name="<raw return>"),
                        args=[],
                        keywords=[]
                    )
                )
            )
        return ast

class LinenoFixer(NodeTransformer):

    def __init__(self, delta: int):
        self._delta = delta

    def visit(self, node: AST) -> Any:
        node = self.generic_visit(node)
        if hasattr(node, "lineno"):
            node.lineno += self._delta
        if hasattr(node, "end_lineno"):
            node.end_lineno += self._delta
        return node


def trim_indent(code: str):
    fl = code.split('\n', 2)[0]
    n = len(fl) - len(fl.lstrip())
    return '\n'.join(line[n:] for line in code.split('\n'))


def recompile(func: FunctionType, inline: bool = False) -> Tuple[CodeType, Dict[str, Any]]:
    file = inspect.getfile(func)
    source = trim_indent(inspect.getsource(func))
    lineno = func.__code__.co_firstlineno
    ast = parse_ast("".join(source), file, mode="single")
    tr = MCFTransformer(inline=inline)
    ast = tr.rebuild(ast)
    ast = fix_missing_locations(ast)
    ast = LinenoFixer(delta=lineno).visit(ast)
    outer = compile(ast, file, mode="single")
    ct: CodeType = filter(lambda c: isinstance(c, CodeType), outer.co_consts).__next__()
    ct = CodeTypeRewriter(ct, rewrite_return=not inline).codetype  # TODO rewrite inner ct
    return ct, tr.get_globals()
