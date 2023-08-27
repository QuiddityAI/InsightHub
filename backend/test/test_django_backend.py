"""
Run with "python3 -m test.test_django_backend"
"""

import json
from typing import Callable

from database_client.django_client import get_object_schema
from logic.extract_pipeline import get_pipeline_steps

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Callable):
            return "<function>"
        return json.JSONEncoder.default(self, obj)


schema = get_object_schema(3)

print(json.dumps(schema, indent=4, cls=JSONEncoder))

steps = get_pipeline_steps(schema)

print(json.dumps(steps, indent=4, cls=JSONEncoder))

