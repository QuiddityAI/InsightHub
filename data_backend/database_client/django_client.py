
import requests
import os

from utils.dotdict import DotDict


backend_url = os.getenv("organization_backend_host", "http://localhost:55125")


def get_object_schema(schema_id: int) -> DotDict:
    url = backend_url + '/data_map/object_schema'
    data = {
        'schema_id': schema_id,
    }
    result = requests.post(url, json=data)
    return DotDict(result.json())
