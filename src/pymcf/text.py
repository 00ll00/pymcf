from typing import Any

from pymcf.data import Score, Entity
from pymcf.mc.commands import TextComponent, TextScoreComponent, TextComponentHolder, TextStringComponent, \
    TextSelectorCompoment


def text_component(data: Any, /, **style) -> TextComponent:
    if isinstance(data, Score):
        comp = TextScoreComponent(data.__metadata__)
    elif isinstance(data, Entity):
        comp = TextSelectorCompoment(data.__metadata__)
    else:
        comp = TextStringComponent(str(data))
    if style:
        comp = TextComponentHolder(style, [comp])
    return comp
