from abc import abstractmethod, ABC
from typing import final, Self, Iterator

from pydantic import BaseModel

from ._syntactic import RtBaseExc, RtSysExc, RtNormalExc, RtCfExc, RtUnreachable, RtAnyNormalExc, RtContinue, RtBreak, RtReturn, RtStopIteration


class RtBaseData(ABC):

    def __bool_and__(self, other):
        """
        覆盖此方法以重写 and 运算
        """
        return NotImplemented

    def __bool_or__(self, other):
        """
        覆盖此方法以重写 or 运算
        """
        return NotImplemented

    @abstractmethod
    def __assign__(self, value):
        """
        实现此方法定义运行期数据赋值操作
        """

    @classmethod
    @abstractmethod
    def __create_tmp__(cls) -> Self:
        ...

class RtBaseIterator[V: RtBaseData](RtBaseData, Iterator, ABC):

    @final
    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self) -> V:
        """
        此方法构造迭代器的迭代流程，并且返回迭代对象
        """
