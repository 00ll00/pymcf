from config import Config
from ir import control_flow_expand, simplify
from visualize import draw_ir, dump_context
from ast_ import reform_func, Context, dump
from data.data import ScoreRange, Score, ScoreIdentifier, Name, ScoreBoard
from data.exceptions import RtExc


class RtExc1(RtExc): ...
class RtExc2(RtExc): ...
class RtExc3(RtExc): ...

config = Config(ir_simplify=0, ir_inline_catch=True)

# noinspection PyUnusedLocal
def aaa(a: Score):
    f"say function begin"
    try:
        # for i in range(20):
        for _ in ScoreRange(100):
            if a == 1:
                raise RtExc1
        f"1111111111111111111"
    except:
        f"aaa"
    # finally:
    #     f"pass"
        # return
    f"say function end"

bbb = reform_func(aaa)

with Context("root") as ctx:
    bbb(Score(0))
ctx.finish()

with open("test.html", 'w') as f:
    f.write(dump_context(ctx))

cb = control_flow_expand(ctx.root_scope, Score(identifier=ScoreIdentifier(entity=Name("$bf"), scb=ScoreBoard("$sys"))), config=config)
cb = simplify(cb, config)

# print(dump_config(config))

draw_ir(cb).save("test.dot")