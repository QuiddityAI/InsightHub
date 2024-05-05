import os
from concurrent.futures import ThreadPoolExecutor
import math
from typing import Any, Callable, Iterable
import numpy as np

from utils.dotdict import DotDict


def polar_to_cartesian(r, theta):
    '''
    From: https://stackoverflow.com/a/67939921
    Parameters:
    - r: float, vector amplitude
    - theta: float, vector angle
    Returns:
    - x: float, x coord. of vector end
    - y: float, y coord. of vector end
    '''

    z = r * np.exp(1j * theta)
    x, y = z.real, z.imag

    return np.column_stack([x, y])


def normalize_array(arr: np.ndarray) -> np.ndarray:
    arr = arr - np.min(arr)
    max_element = np.max(arr)
    return arr / max_element if max_element != 0 else arr


def run_in_batches(items: list, batch_size: int, function: Callable) -> list:
    results = []
    for batch_number in range(math.ceil(len(items) / float(batch_size))):
        partial_results = function(items[batch_number * batch_size : (batch_number + 1) * batch_size])
        results += partial_results
    return results


def do_in_parallel(action:Callable, data:Iterable, max_workers:int=20) -> Iterable:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(action, data))
    return results


def run_in_batches_without_result(items: list, batch_size: int, function: Callable):
    for batch_number in range(math.ceil(len(items) / float(batch_size))):
        function(items[batch_number * batch_size : (batch_number + 1) * batch_size])


def get_vector_field_dimensions(field: DotDict):
    return field.generator.embedding_space.dimensions if field.generator else \
        (field.embedding_space.dimensions if field.embedding_space else field.index_parameters.vector_size)


def join_text_source_fields(item: dict, descriptive_text_fields: list[str], field_boundary: str = " ") -> str:
    texts = []
    for field in descriptive_text_fields:
        content = item.get(field, "")
        if not content:
            continue
        if isinstance(content, list):
            texts.append(field_boundary.join(content))
        else:
            texts.append(content)
    return field_boundary.join(texts)


def join_extracted_text_sources(source_texts: list[str | list]) -> str:
    texts = []
    for content in source_texts:
        if not content:
            continue
        if isinstance(content, list):
            texts.append(" ".join(content))
        if isinstance(content, dict):
            # assuming that this is a text chunk with metadata, should be handled better (e.g. with field type)
            texts.append(f'{content.get("prefix")}{content.get("text")}{content.get("suffix")}')
        else:
            texts.append(content)
    return " ".join(texts)


def get_field_from_all_items(items_by_dataset: dict[str, dict[str, dict]], sorted_ids: list[tuple[str, str]], field_name: str, default_value: Any):
    return [items_by_dataset[ds_id][item_id].get(field_name, default_value) for (ds_id, item_id) in sorted_ids]


def load_env_file():
    with open("../.env", "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.strip().split("=")
            os.environ[key] = value


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


def profile_with_viztracer(func):
    from viztracer import VizTracer

    def wrapper(*args, **kwargs):
        with VizTracer(
            output_file=f"trace_{func.__name__}.json",
            max_stack_depth=7,
            ) as tracer:
            ret = func(*args, **kwargs)
        return ret

    # if it seems that only the last part was recorded, there were problably too many events, try to reduce the max_stack_depth
    # open in https://ui.perfetto.dev

    return wrapper
