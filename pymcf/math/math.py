from abc import ABC, abstractmethod
from typing import Tuple


class Numeric(ABC):
    from pymcf.data import Bool

    @abstractmethod
    def __add__(self, other) -> "Numeric":
        ...

    def __radd__(self, other) -> "Numeric":
        return self.__add__(other)

    @abstractmethod
    def __iadd__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __sub__(self, other) -> "Numeric":
        ...

    def __rsub__(self, other) -> "Numeric":
        return -self + other

    @abstractmethod
    def __isub__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __mul__(self, other) -> "Numeric":
        ...

    def __rmul__(self, other) -> "Numeric":
        return self.__mul__(other)

    @abstractmethod
    def __imul__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __floordiv__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __rfloordiv__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __ifloordiv__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __truediv__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __rtruediv__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __itruediv__(self, other) -> "Numeric":
        ...

    @abstractmethod
    def __pos__(self) -> "Numeric":
        ...

    @abstractmethod
    def __neg__(self) -> "Numeric":
        ...

    @abstractmethod
    def __abs__(self) -> "Numeric":
        ...

    @abstractmethod
    def __lt__(self, other) -> Bool:
        ...

    @abstractmethod
    def __gt__(self, other) -> Bool:
        ...

    @abstractmethod
    def __le__(self, other) -> Bool:
        ...

    @abstractmethod
    def __ge__(self, other) -> Bool:
        ...

    @abstractmethod
    def __eq__(self, other) -> Bool:
        ...


class Integral(Numeric, ABC):

    @abstractmethod
    def __mod__(self, other) -> "Integral":
        ...

    @abstractmethod
    def __imod__(self, other) -> "Integral":
        ...

    def __divmod__(self, other) -> Tuple["Integral", "Integral"]:
        return self // other, self % other

    @abstractmethod
    def __rshift__(self, other) -> "Integral":
        ...

    @abstractmethod
    def __lshift__(self, other) -> "Integral":
        ...

    @abstractmethod
    def __rrshift__(self, other) -> "Integral":
        ...

    @abstractmethod
    def __rlshift__(self, other) -> "Integral":
        ...
