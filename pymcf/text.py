from typing import Any

from pymcf.data import Score
from pymcf.mc.commands import TextComponent, TextScoreComponent, TextComponentHolder, TextStringComponent


def text_component(data: Any, /, **style) -> TextComponent:
    if isinstance(data, Score):
        comp = TextScoreComponent(data.__metadata__)
    else:
        comp = TextStringComponent(str(data))
    if style:
        comp = TextComponentHolder(style, [comp])
    return comp
