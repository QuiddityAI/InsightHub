
from concurrent.futures import ThreadPoolExecutor
import math
from typing import Callable, Iterable
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

    return x, y


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


def join_text_source_fields(item: dict, descriptive_text_fields: list[str]) -> str:
    text = ""
    for field in descriptive_text_fields:
        content = item.get(field, "")
        if not content:
            continue
        if isinstance(content, list):
            text += " ".join(content)
        else:
            text += " " + content
    return text
