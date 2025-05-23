from .commands import ScoreRef, NameRef, ObjectiveRef


class Env:

    def __init__(self):
        self.consts = {}
        self.locals = []

    def get_const_score(self, const: int) -> ScoreRef:
        if const not in self.consts:
            self.consts[const] = ScoreRef(NameRef(f"$const_{const}"),  ObjectiveRef("$sys"))
        return self.consts[const]

    def new_local_score(self) -> ScoreRef:
        index = len(self.locals)
        ref = ScoreRef(NameRef(f"$var_{index}"),  ObjectiveRef("$sys"))
        self.locals.append(ref)
        return ref