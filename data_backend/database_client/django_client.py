
import requests
import os
import json
import base64

from utils.dotdict import DotDict
from utils.custom_json_encoder import CustomJSONEncoder


backend_url = os.getenv("organization_backend_host", "http://localhost:55125")


def get_object_schema(schema_id: int) -> DotDict:
    url = backend_url + '/data_map/object_schema'
    data = {
        'schema_id': schema_id,
    }
    result = requests.post(url, json=data)
    return DotDict(result.json())


def add_stored_map(task_id, user_id, schema_id, name, map_data) -> DotDict:
    url = backend_url + '/data_map/add_stored_map'
    body = {
        'id': task_id,
        'user_id': user_id,
        'schema_id': schema_id,
        'name': name,
        'map_data': base64.b64encode(json.dumps(map_data, cls=CustomJSONEncoder).encode()).decode()
    }
    result = requests.post(url, json=body)
    return result.json()
