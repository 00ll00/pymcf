from abc import ABC, abstractmethod
from typing import final


class Selector(ABC):

    @abstractmethod
    def gen(self):
        ...


@final
class Self(Selector):

    _self = None

    def __new__(cls, *args, **kwargs):
        if Self._self is None:
            Self._self = super(Self, cls).__new__(cls, *args, **kwargs)
        return Self._self

    def gen(self):
        return "@s"
