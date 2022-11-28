import abc
from pymcf.data import InGameData as InGameData, Int as Int, ScoreContainer as ScoreContainer, Scoreboard as Scoreboard
from typing import Any, Optional, Union


class Fixed(InGameData, metaclass=abc.ABCMeta):
    scale: float
    score: Int
    def __init__(self, value: Optional[Union[float, Any]] = ..., entity: Optional[ScoreContainer] = ..., objective: Optional[Scoreboard] = ..., score: Optional[Int] = ..., scale: float = ...) -> None: ...
    def json(self): ...
    def rescale(self, scale: float) -> Fixed: ...