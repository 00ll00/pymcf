# from _ast import UAdd, USub, And, Mult, Or
# from ast import NodeVisitor
# from numbers import Real
#
# from pymcf.ast_ import Call, stmt, Raw, Context, Assign, UnaryOp, BoolOp, BinOp
# from pymcf.data import Score, Bool
# from pymcf.ir import code_block, BasicBlock, MatchJump
# from pymcf.ir.codeblock import JmpEq, JmpNotEq
#
# """
# minecraft 1.12.5
# """
#
# def dump_score(score: Score):
#     return f"{score.identifier.entity} {score.identifier.scb}"
#
#
# class Range:
#     def __init__(self, vmin: int = None, vmax: int = None):
#         self.vmin = vmin
#         self.vmax = vmax
#     def __str__(self):
#         return f"{self.vmin}..{self.vmax}"
#
#
# class RunIf(Call):
#     def __init__(self, func, cond, value_range: Range, *args, **kwargs):
#         self.cond = cond
#         self.value_range = value_range
#         super().__init__(func, *args, **kwargs)
#
#
# class RunIfNot(Call):
#     def __init__(self, func, cond, value_range: Range, *args, **kwargs):
#         self.cond = cond
#         self.value_range = value_range
#         super().__init__(func, *args, **kwargs)
#
#
#
# class Translator:
#
#     def translate(self, s) -> list[str]:
#         cls = s.__class__.__name__
#         translator = getattr(self, "translate_" + cls)
#         return translator(s)
#
#     def translate_BasicBlock(self, cb: BasicBlock) -> list[str]:
#         ops: list[stmt] = cb.ops.copy()
#         if cb.direct is not None:
#             ops.append(Call(cb.direct, _offline=True))
#         if cb.cond is not None:
#             if cb.true is not None:
#                 ops.append(RunIfNot(cb.true, cb.cond, Range(0, 0), _offline=True))
#             if cb.false is not None:
#                 ops.append(RunIf(cb.false, cb.cond, Range(0, 0), _offline=True))
#
#         res = []
#         [*self.translate(op) for op in ops]
#
#     def visit_MatchJump(self, cb: MatchJump) -> list[str]:
#         for case in cb.cases:
#             if isinstance(case, JmpEq):
#                 return self.translate(RunIf(case.target, cb.flag, case.value))
#             elif isinstance(case, JmpNotEq):
#                 return self.translate(RunIfNot(case.target, cb.flag, case.value))
#             else:
#                 raise NotImplementedError()
#
#     def visit_Raw(self, op: Raw):
#         self.add_raw(op.code)
#
#     def visit_Call(self, cb: Call):
#         if isinstance(cb.func, Context):
#             self.add_raw(f"function {cb.func.name}")
#         else:
#             raise NotImplementedError()
#
#     def visit_RunIf(self, op: RunIf):
#         if isinstance(op.func, Context):
#             if isinstance(op.cond, Score):
#                 self.add_raw(f"execute if score {dump_score(op.cond)} matches {op.value_range} run {op.func.name}")
#             else:
#                 raise NotImplementedError()
#         else:
#             raise NotImplementedError()
#
#     def visit_RunIfNot(self, op: RunIfNot):
#         if isinstance(op.func, Context):
#             if isinstance(op.cond, Score):
#                 self.add_raw(f"execute unless score {dump_score(op.cond)} matches {op.value_range} run {op.func.name}")
#             else:
#                 raise NotImplementedError()
#         else:
#             raise NotImplementedError()
#
#     def visit_Assign(self, op: Assign):
#         if isinstance(op.target, Score):
#             if isinstance(op.value, Score):
#                 self.add_raw(f"scoreboard players operation {dump_score(op.target)} = {dump_score(op.value)}")
#             elif isinstance(op.value, Real):
#                 self.add_raw(f"scoreboard players set {dump_score(op.target)} = {int(op.value)}")
#             else:
#                 raise NotImplementedError()
#         else:
#             raise NotImplementedError()
#
#     def visit_UnaryOp(self, op: UnaryOp):
#         if isinstance(op.target, Score):
#             match op.op:
#                 case UAdd():
#                     self.add_raw(f"scoreboard players operation {dump_score(op.target)} = {dump_score(op.value)}")
#                 case USub():
#                     self.add_raw(f"scoreboard players set {dump_score(op.target)} 0")
#                     self.add_raw(f"scoreboard players operation {dump_score(op.target)} -= {dump_score(op.value)}")
#                 case _:
#                     raise NotImplementedError()
#         else:
#             raise NotImplementedError()
#
#     def visit_BoolOp(self, op: BoolOp):
#         assert isinstance(op.left, Bool) and isinstance(op.right, Bool)
#         match op.op:
#             case And():
#                 self.add_raw(f"execute store success score {dump_score(op.target)} if score {op.left} matches 1 if score {op.right} matches 1")
#             case Or():
#                 self.visit(Assign(op.target, op.left))
#                 self.add_raw(f"execute if score {dump_score(op.target)} matches 0 store success score {dump_score(op.target)} if score {op.right} matches 0")