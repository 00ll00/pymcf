from abc import abstractmethod, ABC
from typing import Iterator, TypeVar, final, Generic


class InGameObj(ABC):
    """
    base of all in game class.

    only InGameObj, Tuple[InGameObj, ... ] and None can be returned by mcfunction.
    """

    def _compatible_to_(self, other) -> bool:
        """
        different type could have compatible structure, e.g. Score and NbtInt
        """
        return type(self) is type(other)

    @abstractmethod
    def _transfer_to_(self, other):
        """
        for mcfunction passing arguments.

        use **mcfunction operations** to copy value from `self` to `other`.

        `other` is compatible `self`.
        """
        ...

    @abstractmethod
    def _structure_new_(self) -> "InGameObj":
        """
        make an arg receiver of reference. copy should be compatible to reference.

        this method should not create mcfunction operations.

        for mcfunction transfer argument and result.
        """
        ...

    def _make_copy_(self) -> "InGameObj":
        """
        make a copy of self using mcfunction operations.
        """
        res = self._structure_new_()
        self._transfer_to_(res)
        return res


class InGameData(InGameObj, ABC):
    """
    indicate a data object is an in game data container.
    """
    ...

    @abstractmethod
    def set_value(self, value):
        """
        equivalent to assignment statement in mcfunction context.
        """
        ...

    def __bool_and__(self, other):
        """
        called on `and` operator.
        self is treated as `True` by default.
        """
        return other

    def __bool_or__(self, other):
        """
        called on `or` operator.
        self is treated as `True` by default.
        """
        return True

    def __bool_not__(self):
        """
        called on `not` operator.
        self is treated as `True` by default.
        """
        return False


class InGameEntity(InGameObj, ABC):
    """
    indicate a class is an in game entity class.
    this class should not be implemented by user, use Entity instead.
    """

    @abstractmethod
    def __enter__(self):
        self.identifier.__enter__()

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.identifier.__exit__(exc_type, exc_val, exc_tb)

    def __str__(self):
        return str(self.identifier)

    def _compatible_to_(self, other):
        return type(other) is InGameEntity


class InGameIterator(InGameObj, ABC):
    """
    indicate an iterator is an in game iterator. InGameIter will wrap `for` expression in mcfunction way.
    do not call `__iter__` or `__next__` function manually.

    pymcf only create a base block file for hole for statement, iteration file management should be implemented in
    `_iter_init_`, `_iter_next_` and `_iter_end_` manually.
    """

    @final
    def __iter__(self):
        return self

    @final
    def __next__(self):  # for type hint only
        raise TypeError(f"InGameIter object cannot be used in this iteration statement.")

    @abstractmethod
    def _iter_init_(self):
        """
        call before entering iteration.
        """
        ...

    @abstractmethod
    def _iter_next_(self, brk_flag) -> InGameData:
        """
        return iterating var.

        if iter reach end, set value BreakLevel.BREAK to brk_flag.
        """
        ...

    @abstractmethod
    def _iter_end_(self):
        """
        call after entering iteration.
        """
        ...

    def _compatible_to_(self, other):
        return type(self) == type(other)
