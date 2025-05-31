from collections import defaultdict

from .ast_ import RtBaseExc
from .ast_.runtime import RtNormalExc, _RtNormalExcMeta

_all_cls: list[type["RtExc"]] = []
_all_instance = defaultdict(list)

_confirmed = False


class _RtExcMeta(_RtNormalExcMeta):

    def __new__(mcls, name, bases, namespace, **kwargs):
        assert not _confirmed
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        cls._errno_range = NotImplemented
        _all_cls.append(cls)
        return cls

    @property
    def errno_range(cls):
        assert _confirmed
        return cls._errno_range

class RtExc(RtNormalExc, metaclass=_RtExcMeta):
    def __new__(cls, *args, **kwargs):
        assert not _confirmed
        self = super().__new__(cls)
        _all_instance[type(self)].append(self)
        self._errno = NotImplemented
        return self

    def __init__(self, *args, **kwargs):
        super(RtBaseExc, self).__init__(*args, **kwargs)

    @property
    def errno(self):
        assert _confirmed
        return self._errno


def confirm():
    global _confirmed
    assert not _confirmed
    _confirmed = True

    if len(_all_instance) == 0:
        return

    max_instance = max(len(v) for v in _all_instance.values())
    cls_shift = 10 ** len(str(max_instance))

    RtExc._errno_range = [1, 1]
    for cls in _all_cls:
        flag = False
        for base in cls.mro()[1:]:
            if issubclass(base, RtExc):
                base._errno_range[1] += 1
                if not flag:
                    cls._errno_range = [base._errno_range[1], base._errno_range[1]]
                    flag = True

    for cls, excs in _all_instance.items():
        cls_base = cls.errno_range[0] * cls_shift
        for i, exc in enumerate(excs):
            exc._errno = cls_base + i

    for cls in _all_cls:
        cls._errno_range = (cls._errno_range[0] * cls_shift, (cls._errno_range[1] + 1) * cls_shift - 1)