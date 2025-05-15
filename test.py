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

config = Config(ir_simplify=3, ir_inline_catch=True)

# noinspection PyUnusedLocal
def aaa():
    f"function begin"
    for i in ScoreRange(0, 100):
        if i > 10:
            continue
        if i > 20:
            break
        i = 100000000
        a = Score(i)
    else:
        raise RtExc2()
    f"function end"

bbb = reform_func(aaa)

with Context("root") as ctx:
    bbb()
    print(dump(ctx.root_scope, indent=4))

cb = control_flow_expand(ctx.root_scope, Score(identifier=ScoreIdentifier(entity=Name("$bf"), scb=ScoreBoard("$sys"))), config=config)
cb = simplify(cb, config)

# print(dump_config(config))

GraphVizDumper(cb).graph.save("test.dot")