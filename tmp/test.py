from pymcf.config import Config
from pymcf.ir import control_flow_expand, simplify
from pymcf.visualize import draw_ir, dump_context
from pymcf.ast_ import reform_func, Context
from pymcf.data import Score, ScoreIdentifier, Name, ScoreBoard
from pymcf.data.exceptions import RtExc


class RtExc1(RtExc): ...
class RtExc2(RtExc): ...
class RtExc3(RtExc): ...

config = Config(ir_simplify=3, ir_inline_catch=False)

# noinspection PyUnusedLocal
def aaa(a: Score):
    f"say function begin"
    try:
        for i in range(10):
            if a == 1:
                return
            if i > 5:
                break
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