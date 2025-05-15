from config import Config, dump_config
from ir import control_flow_expand, simplify
from ir.visualize import GraphVizDumper
from ast_.ast_gen import reform_func
from ast_ import Context, dump, RtContinue, RtBaseExc, RtAnyNormalExc, Call
from data.data import ScoreRange, Score, ScoreIdentifier, Name, ScoreBoard
from data.exceptions import RtExc

class RtExc1(RtExc): ...
class RtExc2(RtExc): ...
class RtExc3(RtExc): ...

config = Config(ir_simplify=3, ir_inline_raise=True)

# noinspection PyUnusedLocal
def aaa():
    f"function begin"
    try:
        a = Score(0)
        if a > 100:
            raise RtExc1()
        elif a > 10:
            return
        elif a > 5:
            Call(None)
        else:
            f"pass"
    except RtExc1:
        f"11111"
    except RtExc2:
        f"22222"
    else:
        f"ELSE"
    f"function end"

bbb = reform_func(aaa)

with Context("root") as ctx:
    bbb()
    # print(dump(ctx.root_scope, indent=4))

cb = control_flow_expand(ctx.root_scope, Score(identifier=ScoreIdentifier(entity=Name("$bf"), scb=ScoreBoard("$sys"))), config=config)
cb = simplify(cb, config)

# print(dump_config(config))

GraphVizDumper(cb).graph.save("test.dot")