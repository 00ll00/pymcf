from numbers import Number
from typing import Optional, Any

from pymcf.data import InGameData, ScoreContainer, Scoreboard, Int, Bool as Bool
from pymcf.math.math import Numeric


class Fixed(InGameData, Numeric):
    """
    fixed point number TODO
    """

    def __add__(self, other) -> "Fixed":
        res = Fixed(self)
        if isinstance(other, Int):
            res.score += (other * self.scale)
        elif isinstance(other, Fixed):
            res.rescale(max(self.scale, other.scale))
            res.score += Fixed(other).rescale(max(self.scale, other.scale)).score
        elif isinstance(other, Number):
            res.score += (other * self.scale)
        else:
            raise TypeError
        return res

    def __iadd__(self, other) -> "Fixed":
        if isinstance(other, Int):
            self.score += other * self.scale
        elif isinstance(other, Fixed):
            self.rescale(max(self.scale, other.scale))
            self.score += Fixed(other).rescale(max(self.scale, other.scale)).score
        elif isinstance(other, Number):
            self.score += other * self.scale
        else:
            raise TypeError
        return self

    def __sub__(self, other) -> "Fixed":
        res = Fixed(self)
        if isinstance(other, Int):
            res.score -= (other * self.scale)
        elif isinstance(other, Fixed):
            res.rescale(max(self.scale, other.scale))
            res.score -= Fixed(other).rescale(max(self.scale, other.scale)).score
        elif isinstance(other, Number):
            res.score -= (other * self.scale)
        else:
            raise TypeError
        return res

    def __isub__(self, other) -> "Fixed":
        if isinstance(other, Int):
            self.score -= (other * self.scale)
        elif isinstance(other, Fixed):
            self.rescale(max(self.scale, other.scale))
            self.score -= Fixed(other).rescale(max(self.scale, other.scale)).score
        elif isinstance(other, Number):
            self.score -= (other * self.scale)
        else:
            raise TypeError
        return self

    def __mul__(self, other) -> "Fixed":
        res = Fixed(self)
        if isinstance(other, Int):
            res.score *= other
        elif isinstance(other, Fixed):
            res.scale *= other.scale
            res.score *= other.score
        elif isinstance(other, Number):
            res.score *= other
        else:
            raise TypeError
        return res

    def __imul__(self, other) -> "Fixed":
        if isinstance(other, Int):
            self.score *= other
        elif isinstance(other, Fixed):
            self.scale *= other.scale
            self.score *= other.score
        elif isinstance(other, Number):
            self.score *= other
        else:
            raise TypeError
        return self

    def __floordiv__(self, other) -> Int:
        res = Fixed(self)
        if isinstance(other, Int):
            res.score //= other
        elif isinstance(other, Fixed):
            res.scale /= other.scale
            res.score //= other.score
        elif isinstance(other, Number):
            res.score //= other
        else:
            raise TypeError
        return res

    def __rfloordiv__(self, other) -> Int:  # TODO
        res = Fixed(self)
        if isinstance(other, Int):
            res.score //= other
        elif isinstance(other, Fixed):
            res.scale /= other.scale
            res.score //= other.score
        elif isinstance(other, Number):
            res.score //= other
        else:
            raise TypeError
        return res

    def __ifloordiv__(self, other) -> Int:
        if isinstance(other, Int):
            self.score //= other
        elif isinstance(other, Fixed):
            self.scale /= other.scale
            self.score //= other.score
        elif isinstance(other, Number):
            self.score //= other
        else:
            raise TypeError
        return self

    def __truediv__(self, other) -> Numeric:
        pass

    def __rtruediv__(self, other) -> Numeric:
        pass

    def __itruediv__(self, other) -> Numeric:
        pass

    def __pos__(self) -> "Fixed":
        return Fixed(self)

    def __neg__(self) -> "Fixed":
        res = Fixed(self)
        res.scale = - res.scale
        return res

    def __abs__(self) -> "Fixed":
        res = Fixed(self)
        res.scale = abs(res.scale)
        res.score = abs(res.score)
        return res

    def __lt__(self, other) -> Bool:
        pass

    def __gt__(self, other) -> Bool:
        pass

    def __le__(self, other) -> Bool:
        pass

    def __ge__(self, other) -> Bool:
        pass

    def __eq__(self, other) -> Bool:
        pass

    def __init__(self,
                 value: Optional[float | Any] = None,
                 entity: Optional[ScoreContainer] = None,
                 objective: Optional[Scoreboard] = None,
                 scale: float = 1e3,
                 ):
        assert scale != 0
        self.scale = scale
        if value is None:
            self.score = Int()
        elif isinstance(value, Int):
            if scale == 1:
                self.score = Int(value, entity, objective)
            else:
                self.score = Int(value * scale, entity, objective)
        elif isinstance(value, Fixed):
            if (scale / value.scale) == 1:
                self.score = Int(value.score, entity, objective)
            else:
                self.score = Int(value.score * (scale / value.scale), entity, objective)
        elif isinstance(value, Number):
            self.score = Int(int(value * scale), entity, objective)

    def _compatible_to_(self, other):
        return isinstance(other, Fixed) and other.scale == self.scale

    def _transfer_to_(self, other: "Fixed"):
        other.score.set_value(self.score)

    def _structure_new_(self) -> "Fixed":
        return Fixed(scale=self.scale)

    def set_value(self, value):
        if isinstance(value, Number):
            self.score.set_value(int(value * self.scale))
        elif isinstance(value, Int):
            self.score.set_value(value * self.scale)
        elif isinstance(value, Fixed):
            self.score.set_value(value.score)
            self.scale = value.scale

    def rescale(self, scale: float):
        if scale > self.scale:
            self.score *= (scale / self.scale)
        elif scale < self.scale:
            self.score /= (self.scale / scale)
        return self

    def __str__(self):
        return str(self.score)

    def json(self):
        return self.score.json

