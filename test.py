from config import Config
from ir import control_flow_expand, simplify
from visualize import draw_ir, dump_context
from ast_ import reform_func, Context, dump
from data.data import ScoreRange, Score, ScoreIdentifier, Name, ScoreBoard
from data.exceptions import RtExc


class RtExc1(RtExc): ...
class RtExc2(RtExc): ...
class RtExc3(RtExc): ...

config = Config(ir_simplify=3, ir_inline_catch=True)

# noinspection PyUnusedLocal
def aaa():
    f"say function begin"
    try:
        for i in ScoreRange(100):
            if i == 10:
                raise RtExc1
            elif i == 20:
                raise RtExc2
            elif i == 30:
                raise RtExc3
            else:
                break
    except RtExc as e:
        f"handle"
    else:
        return
    f"say function end"

bbb = reform_func(aaa)

with Context("root") as ctx:
    bbb()
ctx.finish()

with open("test.html", 'w') as f:
    f.write(dump_context(ctx))

cb = control_flow_expand(ctx.root_scope, Score(identifier=ScoreIdentifier(entity=Name("$bf"), scb=ScoreBoard("$sys"))), config=config)
cb = simplify(cb, config)

# print(dump_config(config))

draw_ir(cb).save("test.dot")