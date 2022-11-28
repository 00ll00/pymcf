

class staticproperty:

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func()


class lazy:

    def __init__(self, func):
        self.func = func
        self.loaded = False
        self.value = None

    def __call__(self, *args, **kwargs):
        if not self.loaded:
            self.loaded = True
            self.value = self.func(*args, **kwargs)
        return self.value


_ParamEmpty = object()
"""
object witch use as a default parameter to replace `None` when `None` is working as an useful signal.

def fun(x=_ParamEmpty):
    self.x = x if x is not _ParamEmpty else ...
"""
