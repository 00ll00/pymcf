from pymcf.data.score import Score
from pymcf.data.data import InGameIterator, InGameData
from pymcf._frontend import BreakLevel


class ScoreRange(InGameIterator[int]):

    def __init__(self, start, stop, step):
        self.start = start
        self.stop = stop
        self.step = step
        self.iter_var = None

    def _iter_init(self):
        self.iter_var = Score(self.start)

    def _iter_next(self, brk_flag: Score) -> InGameData:
        self.iter_var += self.step
        if self.iter_var >= self.stop:
            brk_flag.set_value(BreakLevel.BREAK.value)
        return self.iter_var
