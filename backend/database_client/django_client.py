
import requests

from utils.dotdict import DotDict


backend_url = "http://localhost:55125"


def get_object_schema(schema_id: int) -> DotDict:
    url = backend_url + '/data_map/object_schema'
    data = {
        'schema_id': schema_id,
    }
    result = requests.post(url, json=data)
    return DotDict(result.json())
