from pymcf.data import Score
from pymcf.entity import Marker


def randint(a: int, b: int) -> Score:  # TODO simplify later
    res = Score()
    tmp = Marker((0, 0, 0), None)
    res.set_value(tmp.nbt.UUID[0])
    tmp.kill()
    res %= (b-a)
    res += a
    return res
