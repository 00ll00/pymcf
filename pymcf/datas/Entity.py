from collections import defaultdict


class Entity:
    pass


class ScoreEntity(Entity):

    group_count = defaultdict(int)

    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def new_dummy(group: str = "dummy"):
        ScoreEntity.group_count[group] += 1
        return ScoreEntity(f'${group}_' + str(ScoreEntity.group_count[group]))
