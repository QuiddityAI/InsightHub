from typing import Any, Iterable
from copy import deepcopy

from .models import ObjectField


def get_vector_field_dimensions(field: ObjectField):
    return field.generator.embedding_space.dimensions if field.generator and field.generator.embedding_space else \
        (field.embedding_space.dimensions if field.embedding_space else (field.index_parameters or {}).get('vector_size'))


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
        elif isinstance(val, Iterable):
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
