import inspect
from _ast import If, IfExp, FunctionDef, Call, Name, expr, Load, Assign, Store, stmt, arguments, Expr, Pass, With, \
    withitem, Constant, Or, BoolOp, Attribute, Nonlocal, Return, AnnAssign, Compare, And, NamedExpr, Assert, boolop, Not, FormattedValue
from abc import ABC
from ast import parse as parse_ast, AST, NodeTransformer, fix_missing_locations
from types import FunctionType, CodeType
from typing import Any, Dict, Tuple, Set, final, List

from .context import MCFContext
from .ct_rewrite import CodeTypeRewriter
from pymcf.data import InGameData, InGameObj, Score, ScoreDummy
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
    __current: "CtxManager" = None
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
    def send_break(brk_lvl: BreakLevel) -> stmt:
        CtxManager.__brkflg_count += 1
        flag_name = f"$bf_{CtxManager.__brkflg_count}"
        brk_flag = Score(ScoreDummy(flag_name))
        CtxManager.__current.receive_break(brk_flag, brk_lvl)
        return Expr(
            Call(
                func=MCFTransformer.Const(CtxManager._send_break),
                args=[
                    MCFTransformer.Const(brk_flag),
                    Constant(value=brk_lvl.value)
                ],
                keywords=[]
            )
        )

    def __enter__(self):
        self.parent = CtxManager.__current
        CtxManager.__current = self
        MCFContext.new_file()

    def __exit__(self, exc_type, exc_val, exc_tb):
        CtxManager.__current = self.parent
        MCFContext.exit_file()
        self.after_exit()

    def after_exit(self):
        run = CallFunctionOp(MCFContext.last_file().name, offline=True)
        for flag in self.brk_flags:
            run = IfScoreLTValueRunOp(flag, 1, run, offline=True)
        ExecuteOp(run)

    def receive_break(self, brk_flag, brk_lvl: BreakLevel):
        self.brk_flags.add(brk_flag)
        self.parent.receive_break(brk_flag, brk_lvl)


class BranchCtxManager(CtxManager):
    """
    manage branch statement like `if ... else ...`.
    only check condition, and decide with branch to run.
    """

    def __init__(self, is_ingame: bool, cond_var: Score, on_true: bool):
        super().__init__()
        self.is_ingame = is_ingame
        self.cond_var = cond_var
        self.on_true = on_true

    def __enter__(self):
        if self.is_ingame:
            super(BranchCtxManager, self).__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_ingame:
            super(BranchCtxManager, self).__exit__(exc_type, exc_val, exc_tb)

    def receive_break(self, brk_flag, brk_lvl: BreakLevel):
        # don't record any break
        self.parent.receive_break(brk_flag, brk_lvl)

    def after_exit(self):
        run_op = IfScoreGEValueRunOp if self.on_true else IfScoreLTValueRunOp
        run_op(self.cond_var, 1, CallFunctionOp(MCFContext.last_file().name, offline=True))


class FuncCtxManager(CtxManager):
    """
    manage function def
    """

    def after_exit(self):
        return

    def receive_break(self, brk_flag, brk_lvl: BreakLevel):
        return


class MCFTransformer(NodeTransformer):
    _current: "MCFTransformer"

    def __init__(self):
        super(MCFTransformer, self).__init__()
        self._obj_count = 0
        self._glb = {}
        self._helper_funcs = []
        self._helper_vars = []
        MCFTransformer._current = self

    def rebuild(self, ast: AST) -> AST:
        ast = self.visit(ast)
        func_body = ast.body[0].body
        for f in self._helper_funcs:
            func_body.insert(0, f)
        for v in self._helper_vars:
            func_body.insert(0, AnnAssign(target=Name(id=v, ctx=Store()), annotation=Constant(value=""), simple=1))

        return ast

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
    def Const(obj: Any) -> Name:
        curr = MCFTransformer._current
        if obj in curr._glb.values():
            name = (k for k, v in curr._glb.items() if v is obj).__next__()
        else:
            name = curr.new_obj_name()
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

    def _build_if_stmt(self, test: expr, body: List[stmt], orelse: List[stmt], lineno: int, no_ingame: bool = False) -> stmt:
        # this should not rewrite into function def and call, break / continue statement will be misleading

        has_else = len(orelse) > 0

        # cond var
        assign_cond = Assign(
            targets=[
                Name(id=(name_cond_var := self.new_obj_name()), ctx=Store())
            ],
            value=test
        )

        # assert if ingame var not allowed
        no_ingame_assert = Assert(
            test=self.IsInGameObjExpr(Name(id=name_cond_var, ctx=Load())),
            msg=f"InGameObj is not allowed in condition here. (at line: {lineno})"
        ) if no_ingame else Pass()

        # cond ingame var
        assign_cond_ingame = Assign(
            targets=[
                Name(id=(name_cond_ingame_var := self.new_obj_name()), ctx=Store())
            ],
            value=Call(func=self.Const(isinstance), args=[Name(id=name_cond_var, ctx=Load()), self.Const(InGameData)],
                       keywords=[])
        )

        # cond fail var, use a variable to avoid get conditions value twice
        assign_cond_fail = Assign(
            targets=[
                Name(id=(name_cond_fail_var := self.new_obj_name()), ctx=Store())
            ],
            value=Constant(value=False)
        )

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
                Assign(
                    targets=[
                        Name(id=name_cond_fail_var, ctx=Store())
                    ],
                    value=Constant(value=True)
                )
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

        name_res = self.new_obj_name()

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

    def visit_If(self, node: If) -> stmt:
        node = self.generic_visit(node)
        return self._build_if_stmt(node.test, node.body, node.orelse, node.lineno)

    def visit_IfExp(self, node: IfExp) -> expr:  # TODO ingame if-expr test may not work as expected
        node = self.generic_visit(node)
        return self._build_if_expr(node.test, node.body, node.orelse, node.lineno, no_ingame=True)

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

    def visit_Not(self, node: Not) -> expr:
        # make `__bool_not__` call if contains InGameData
        node = self.generic_visit(node)

        return Call(
            func=self.Const(_wrapped_not),
            args=[node],
            keywords=[],
            lineno=node.lineno
        )

    # def visit_Match(self, node: Match) -> stmt: # TODO match

    # def visit_While(self, node: While) -> stmt:
    #     node = self.generic_visit(node)
    #
    #     new_node = With(
    #         items=[
    #             withitem(context_expr=Call(func=self.Const(CtxManager), args=[], keywords=[]))
    #         ],
    #         body=[
    #
    #         ],
    #         lineno=node.lineno
    #     )
    #
    #     return new_node

    def visit_FunctionDef(self, node: FunctionDef) -> Any:
        node = self.generic_visit(node)
        node.decorator_list.clear()  # TODO remove @mcfunction only
        node.body = [
            With(
                items=[
                    withitem(context_expr=Call(func=self.Const(FuncCtxManager), args=[], keywords=[]))
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


def recompile(func: FunctionType) -> Tuple[CodeType, Dict[str, Any]]:
    file = inspect.getfile(func)
    source = trim_indent(inspect.getsource(func))
    lineno = func.__code__.co_firstlineno
    ast = parse_ast("".join(source), file, mode="single")
    tr = MCFTransformer()
    ast = tr.rebuild(ast)
    ast = fix_missing_locations(ast)
    ast = LinenoFixer(delta=lineno).visit(ast)
    ct: CodeType = compile(ast, file, mode="single").co_consts[0]
    ct = CodeTypeRewriter(ct).codetype
    return ct, tr.get_globals()
