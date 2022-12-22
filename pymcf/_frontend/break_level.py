from enum import Enum
from functools import total_ordering


@total_ordering
class BreakLevel(Enum):
    PASS = 0
    CONTINUE = 1
    BREAK = 2
    RETURN = 3
    RAISE = 4

    @staticmethod
    def from_value(value):
        if isinstance(value, int):
            match value:
                case 0:
                    return BreakLevel.PASS
                case 1:
                    return BreakLevel.CONTINUE
                case 2:
                    return BreakLevel.BREAK
                case 3:
                    return BreakLevel.RETURN
                case 4:
                    return BreakLevel.RAISE
                case _:
                    return ValueError()
        elif isinstance(value, BreakLevel):
            return value
        else:
            raise TypeError()

    def __int__(self):
        return self.value

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        return self.value < other.value

