from pymcf.data import Score


class Env:

    def __init__(self):
        self.consts = {}

    def get_const_score(self, const: int) -> Score:
        if const not in self.consts:
            self.consts[const] = Score(f"$const{const}", "$sys")
        return self.consts[const]