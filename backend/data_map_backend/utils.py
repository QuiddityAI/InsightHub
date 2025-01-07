from typing import Any, Iterable
from copy import deepcopy
import os
import uuid
from uuid import uuid5

import numpy as np

from .models import DatasetField


def get_vector_field_dimensions(field: DatasetField):
    return field.generator.embedding_space.dimensions if field.generator and field.generator.embedding_space else \
        (field.embedding_space.dimensions if field.embedding_space else (field.index_parameters or {}).get('vector_size'))


class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    # from https://stackoverflow.com/a/23689767

    def __getattr__(self, name: str) -> Any:
        val = dict.get(self, name)
        if type(val) is DotDict:
            return val
        elif type(val) is dict:
            return DotDict(val)
        elif isinstance(val, str) or isinstance(val, bytes):
            return val
        elif isinstance(val, np.ndarray):
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
        elif isinstance(val, np.ndarray):
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


# a decorator to profile a function using cProfile and print the results to stdout:
def profile(func):
    import cProfile
    import pstats
    import io
    import logging

    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        ret = func(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.sort_stats('cumulative')
        ps.print_stats(10)
        logging.warning(s.getvalue())
        return ret

    return wrapper


def profile_with_viztracer(*d_args, max_stack_depth: int | None=7, **d_kwargs):
    from viztracer import VizTracer
    if max_stack_depth:
        d_kwargs['max_stack_depth'] = max_stack_depth

    def decorator(func):
        def wrapper(*args, **kwargs):
            with VizTracer(
                *d_args,
                output_file=f"trace_{func.__name__}.json",
                **d_kwargs,
                ) as tracer:
                ret = func(*args, **kwargs)
            return ret

        # if it seems that only the last part was recorded, there were problably too many events, try to reduce the max_stack_depth
        # open in https://ui.perfetto.dev

        return wrapper
    return decorator


BACKEND_AUTHENTICATION_SECRET = os.getenv("BACKEND_AUTHENTICATION_SECRET", "not_set")


def is_from_backend(request):
    return request.headers.get("Authorization") == BACKEND_AUTHENTICATION_SECRET


def pk_to_uuid_id(pk: str) -> str:
    return str(uuid5(uuid.NAMESPACE_URL, pk))
