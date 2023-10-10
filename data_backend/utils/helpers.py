
import math
from typing import Callable
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


def get_vector_field_dimensions(field: DotDict):
    return field.generator.embedding_space.dimensions if field.generator else \
        (field.embedding_space.dimensions if field.embedding_space else field.index_parameters.vector_size)
