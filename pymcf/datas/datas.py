from abc import abstractmethod, ABC
from typing import Iterator, TypeVar, final, Generic


class InGameData(ABC):
    """
    indicate a data object is an in game data container.
    """

    @abstractmethod
    def is_same_type(self, other):
        ...

    @abstractmethod
    def copy_to(self, other):
        """
        for mcfunction passing arguments
        """
        ...

    @abstractmethod
    def copy(self):
        """
        make a copy of self. copy should have same type of self.

        for mcfunction transfer result.
        """
        ...


T = TypeVar("T", bound=InGameData)


class InGameIter(Generic[T], Iterator[T], ABC):
    """
    indicate an iterator is an in game iterator.

    InGameIter will wrap `for` expression in mcfunction way.
    """

    @final
    def __iter__(self):  # for type hint only
        return self

    @final
    def __next__(self) -> T:  # for type hint only
        pass

    @abstractmethod
    def iter_init(self):
        ...

    @abstractmethod
    def iter_next(self, brk_flag) -> InGameData:
        """
        return iterating var.

        if iter reach end, set brk_flag  breaklevel.BREAK.
        """
        ...
