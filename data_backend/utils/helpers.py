
import numpy as np


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


def normalize_array(arr):
    arr = arr - np.min(arr)
    max_element = np.max(arr)
    return arr / max_element if max_element != 0 else arr