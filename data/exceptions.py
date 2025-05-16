from ast_.runtime import RtNormalExc

_all = {}
_errno_count = 0


class RtExc(RtNormalExc):
    _errno = 0
    def __init_subclass__(cls, *, __errno=None, **kwargs):
        global _errno_count
        if __errno is None:
            _errno_count += 1
            __errno = _errno_count
        assert __errno != 0, "异常id不能为0"
        assert __errno not in _all, f"出现相同id的异常:{__errno}, {cls}, {_all[__errno]}"
        cls._errno = __errno
        _all[__errno] = cls
