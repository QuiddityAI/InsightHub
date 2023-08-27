"""
Run with "python3 -m test.test_django_backend"
"""

import json

from database_client.django_client import get_object_schema
from logic.extract_pipeline import get_pipeline_steps


schema = get_object_schema(3)

print(json.dumps(schema, indent=4))

steps = get_pipeline_steps(schema)

print(json.dumps(steps, indent=4))

