import json
from typing import Callable
import uuid

import numpy as np


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, Callable):
            return "<function>"
        return json.JSONEncoder.default(self, obj)


class HumanReadableJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, np.ndarray):
            return f"Array of shape {obj.shape}"
        elif isinstance(obj, Callable):
            return "<function>"
        return json.JSONEncoder.default(self, obj)

