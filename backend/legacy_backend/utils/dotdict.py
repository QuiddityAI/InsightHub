from typing import Any, Iterable, List
from copy import deepcopy

import numpy as np


class DotDict(dict):
    """dot.notation access to dictionary attributes"""

    # from https://stackoverflow.com/a/23689767

    def __getattr__(self, name: str) -> Any:
        val = dict.get(self, name)
        if type(val) is dict:
            return DotDict(val)
        elif isinstance(val, str) or isinstance(val, bytes):
            return val
        elif isinstance(val, Iterable):
            klass = type(val)
            return klass(DotDict(e) if type(e) is dict else e for e in val)  # type: ignore
        else:
            return val

    def __getitem__(self, name: str) -> Any:
        val = dict.__getitem__(self, name)
        if type(val) is dict:
            return DotDict(val)
        elif isinstance(val, str) or isinstance(val, bytes):
            return val
        elif isinstance(val, Iterable) and not isinstance(val, np.ndarray):
            klass = type(val)
            return klass(DotDict(e) if type(e) is dict else e for e in val)  # type: ignore
        else:
            return val

    def values(self):
        val = super(DotDict, self).values()
        return (DotDict(e) if type(e) is dict else e for e in val)  # type: ignore

    __setattr__ = dict.__setitem__  # type: ignore
    __delattr__ = dict.__delitem__  # type: ignore

    def __dir__(self):
        return dir(dict) + list(self.keys())

    def __deepcopy__(self, memo=None):
        # see here: https://stackoverflow.com/a/49902096
        return DotDict(deepcopy(dict(self), memo=memo))


class DotDictSlow(dict):
    # https://stackoverflow.com/a/70665030/913098
    """
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])

    Iterable are assumed to have a constructor taking list as input.
    """

    def __init__(self, *args, **kwargs):
        super(DotDictSlow, self).__init__(*args, **kwargs)

        args_with_kwargs = []
        for arg in args:
            args_with_kwargs.append(arg)
        args_with_kwargs.append(kwargs)
        args = args_with_kwargs

        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v
                    if isinstance(v, dict):
                        self[k] = DotDictSlow(v)
                    elif isinstance(v, str) or isinstance(v, bytes):
                        self[k] = v
                    elif isinstance(v, Iterable):
                        klass = type(v)
                        map_value: List[Any] = []
                        for e in v:
                            map_e = DotDictSlow(e) if isinstance(e, dict) else e
                            map_value.append(map_e)
                        self[k] = klass(map_value)  # type: ignore

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(DotDictSlow, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(DotDictSlow, self).__delitem__(key)
        del self.__dict__[key]

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__.update(d)
