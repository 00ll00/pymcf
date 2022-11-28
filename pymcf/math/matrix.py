from numbers import Number
from typing import Tuple, Sequence

from pymcf import mcfunction, logger
from pymcf.data import InGameData
from .fixed import Fixed
from .math import Numeric


class Mat2D(InGameData):

    def __init__(self, w: int, h: int, dtype=Fixed, values=None):
        self.w: int = w
        self.h: int = h
        self.size: int = w * h
        self.dtype = dtype
        self.data = [self.dtype() for _ in range(self.size)]

        if values is not None:
            self.set_value(values)

    def __str__(self):
        return f"Mat2D[{self.dtype.__qualname__}]({self.w} * {self.h})"

    def _transfer_to_(self, other):
        other.set_value(self)

    def _structure_new_(self) -> "Mat2D":
        return Mat2D(self.w, self.h, dtype=self.dtype)

    def _compatible_to_(self, other):
        return isinstance(other, Mat2D) and self.w == other.w and self.h == other.h

    def copy_to(self, other: "Mat2D"):
        for i in range(self.size):
            other.data[i].set_value(self.data[i])

    def copy(self):
        return Mat2D(self.w, self.h, dtype=self.dtype, values=self.data)

    def set_value(self, values):
        assert len(values) == self.size
        if isinstance(values, Sequence):
            for i in range(self.size):
                self.data[i].set_value(values[i])
        elif isinstance(values, Mat2D):
            for i in range(self.size):
                self.data[i].set_value(values.data[i])
        else:
            raise TypeError()

    def __len__(self):
        return self.size

    def __getitem__(self, index: Tuple[int, int]):
        assert 0 <= index[0] < self.w and 0 <= index[1] < self.h
        return self.data[index[0] * self.w + index[1]]

    def __setitem__(self, index, value):
        assert 0 <= index[0] < self.w and 0 <= index[1] < self.h
        self[index].set_value(value)

    def __iadd__(self, other):
        if isinstance(other, Mat2D):
            assert other.w == self.w and other.h == self.h
            for i in range(self.size):
                self.data[i] += other.data[i]
            return self
        elif isinstance(other, (Number, Numeric)):
            for s in self.data:
                s += other
            return self
        else:
            raise TypeError()

    def __isub__(self, other):
        if isinstance(other, Mat2D):
            assert other.w == self.w and other.h == self.h
            for i in range(self.size):
                self.data[i] -= other.data[i]
            return self
        elif isinstance(other, (Number, Numeric)):
            for s in self.data:
                s -= other
            return self
        else:
            raise TypeError()

    def __imul__(self, other):
        if isinstance(other, (Number, Numeric)):
            for s in self.data:
                s *= other
            return self
        else:
            raise TypeError()

    def __ifloordiv__(self, other):
        if isinstance(other, (Number, Numeric)):
            for s in self.data:
                s //= other
            return self
        else:
            raise TypeError()

    def __itruediv__(self, other):
        if isinstance(other, (Number, Numeric)):
            for s in self.data:
                s /= other
            return self
        else:
            raise TypeError()

    @mcfunction
    def __matmul__(self, other):
        assert isinstance(other, Mat2D) and other.h == self.w
        logger.debug(f"generating mat multiplication for {self} and {other}")
        res = Mat2D(other.w, self.h, self.dtype)
        for i in range(res.h):
            for j in range(res.w):
                res[i, j].set_value(sum(self[i, k] * other[k, j] for k in range(self.w)))
        return res
