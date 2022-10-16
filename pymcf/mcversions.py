from enum import Enum


class MCVer(Enum):

    def __cmp__(self, other):
        return self.value.__cmp__(other.value)

    def __le__(self, other):
        return self.value.__le__(other.value)

    def __lt__(self, other):
        return self.value.__lt__(other.value)

    def __ge__(self, other):
        return self.value.__ge__(other.value)

    def __gt__(self, other):
        return self.value.__gt__(other.value)

    def __repr__(self):
        return self.name.lower()

    def __str__(self):
        return self.name.lower()

    JE_1_19_1 = 1
    JE_1_19_2 = 2
