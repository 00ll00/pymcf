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

        use **mcfunction operations** to copy value of `self` to `other`.

        `other` is compatible `self`.
        """
        ...

    @abstractmethod
    def _new_from_(self) -> "InGameObj":
        """
        make an arg receiver of reference. copy should be compatible to reference.

        for mcfunction transfer result.
        """
        ...


class InGameData(InGameObj, ABC):
    """
    indicate a data object is an in game data container.
    """
    ...


class InGameEntity(InGameObj, ABC):
    """
    indicate a class is an in game entity class.
    """

    def __init__(self, identifier):
        self._identifier = identifier

    @abstractmethod
    def __enter__(self):
        self._identifier.__enter__()

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._identifier.__exit__(exc_type, exc_val, exc_tb)

    def __str__(self):
        return str(self._identifier)

    def _compatible_to_(self, other):
        return type(other) is InGameEntity


T = TypeVar("T", bound=InGameData)


class InGameIter(Generic[T], Iterator[T], InGameObj, ABC):
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
    def _iter_init(self):
        ...

    @abstractmethod
    def _iter_next(self, brk_flag) -> InGameData:
        """
        return iterating var.

        if iter reach end, set brk_flag  breaklevel.BREAK.
        """
        ...

    def _compatible_to_(self, other):
        return type(self) == type(other)
