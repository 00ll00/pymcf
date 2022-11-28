from enum import Enum
from functools import total_ordering


@total_ordering
class BreakLevel(Enum):
    PASS = 0
    CONTINUE = 1
    BREAK = 2
    RETURN = 3
    RAISE = 4

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        return self.value < other.value

