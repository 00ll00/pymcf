class Entity:
    pass


class ScoreEntity(Entity):

    dummy_count = 0

    def __init__(self, name: str):
        self.name = name

    @staticmethod
    def new_sys_dummy():
        ScoreEntity.dummy_count += 1
        return ScoreEntity('$dummy_' + str(ScoreEntity.dummy_count))
