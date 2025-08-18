from pymcf.ast_ import compiler_hint
from pymcf.data import Entity
from pymcf.mcfunction import mcfunction
from pymcf.text import text_component


class DebugStub(compiler_hint):
    """
    用于在可视化视图中定位 debug 语句
    """

    @mcfunction.inline
    def __init__(self, **__):
        f'# debug stub'
        super().__init__(**__)


@mcfunction.inline
def debug(*data, title: str | None = None):
    """
    在游戏中打印任何内容
    :param data: 需要观察的数据
    :param title: 标题
    """
    DebugStub()
    data = list(data)
    for i in reversed(range(1,len(data))):
        data.insert(i, text_component(", ", color="gray"))
    if title is not None:
        f'tellraw @a [{text_component(title, color="gray")},": ", {text_component(data, color="white")}]'
    elif data:
        f'tellraw @a {text_component(data, color="white")}'


@mcfunction.inline
def debug_pos(target: Entity | None = None, pos: str = "~ ~ ~"):
    """
    在游戏中用粒子高亮一个位置
    :param target: 需要高亮的实体，为 None 则高亮函数上下文的当前位置
    :param pos: 相对位置或绝对位置
    """
    DebugStub()
    if target is not None:
        f'execute as {target} at @s run particle minecraft:dust{{scale:1,color:[1,0,1]}} {pos}'
    else:
        f'particle minecraft:dust{{scale:1,color:[1,0,1]}} {pos}'
