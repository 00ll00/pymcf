from enum import Enum

class BreakLevel(Enum):
    PASS: int
    CONTINUE: int
    BREAK: int
    RETURN: int
    RAISE: int
    def __eq__(self, other): ...
    def __lt__(self, other): ...
