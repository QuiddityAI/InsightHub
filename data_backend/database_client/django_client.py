
import logging
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


def add_stored_map(map_id, user_id, schema_id, name, map_data) -> dict:
    url = backend_url + '/data_map/add_stored_map'
    body = {
        'user_id': user_id,
        'schema_id': schema_id,
        'name': name,
        'map_id': map_id,
        'map_data': base64.b64encode(json.dumps(map_data, cls=CustomJSONEncoder).encode()).decode()
    }
    result = requests.post(url, json=body)
    return result.json()


def get_stored_map_data(map_id: str) -> dict | None:
    url = backend_url + '/data_map/stored_map_data'
    data = {
        'map_id': map_id,
    }
    result = requests.post(url, json=data)
    if result.status_code == 200:
        map_data = json.loads(base64.b64decode(result.content.decode()))
        return map_data
    else:
        return None


def get_collection(collection_id: str) -> DotDict | None:
    url = backend_url + '/data_map/get_item_collection'
    data = {
        'collection_id': collection_id,
    }
    result = requests.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find collection: " + str(collection_id))
        return None
    return DotDict(result.json())
