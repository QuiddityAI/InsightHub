"""
Run with "python3 -m test.test_django_backend"
"""

import json
import logging
from typing import Callable
from utils.dotdict import DotDict

from database_client.django_client import get_object_schema
from logic.extract_pipeline import get_pipeline_steps
from database_client.vector_search_engine_client import VectorSearchEngineClient

logging.root.setLevel(logging.INFO)

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Callable):
            return "<function>"
        return json.JSONEncoder.default(self, obj)


schema = DotDict(get_object_schema(3))

print(json.dumps(schema, indent=4, cls=JSONEncoder))

steps = get_pipeline_steps(schema)

print(json.dumps(steps, indent=4, cls=JSONEncoder))

vse_client = VectorSearchEngineClient()

vector_field = 'openai_vector'

# vse_client.remove_schema(schema.id, vector_field)
vse_client.ensure_schema_exists(schema, vector_field)

item = {
    "description": "White crew neck t-shirt",
    "year": 2017,
}

vse_client.upsert_items(schema.id, vector_field, [32, 34], [item, item], [[4, 5, 6, 7]]*2)

items = vse_client.get_items_near_vector(schema.id, vector_field, [7, 8, 4, 5], {}, limit=5)
print(items)

