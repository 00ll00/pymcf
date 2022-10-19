from typing import TypeVar, List, Iterator, Iterable, Generic, Optional


class staticproperty:

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func()


T = TypeVar("T")


class ListReader(Generic[T]):

    def __init__(self, iterable: Iterable[T]):
        self.list = list(iterable)
        self.i = 0

    def __len__(self):
        return len(self.list)

    def __getitem__(self, item):
        return self.list[item]

    def can_read(self) -> bool:
        return self.i < len(self.list)

    def try_read(self) -> Optional[T]:
        if self.can_read():
            return self.read()

    def read(self) -> T:
        if self.i >= len(self.list):
            raise StopIteration()
        res = self.list[self.i]
        self.i += 1
        return res

    def now(self) -> T:
        return self.list[self.i]

    def reset(self):
        self.i = 0

    def back(self, n: int = 1):
        self.i -= n
        return self

    def skip(self, n: int = 1):
        self.i += n
        return self

    def extend(self, iterable):
        self.list.extend(iterable)

    def remove(self, instr):
        self.list.remove(instr)

    def __repr__(self):
        return f"[{self.i}-{len(self.list)}]: {self.now()}"
