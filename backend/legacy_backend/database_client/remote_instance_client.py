import json
from typing import Any

import requests

from data_map_backend.models import Dataset
from data_map_backend.utils import DotDict
from legacy_backend.utils.custom_json_encoder import CustomJSONEncoder


def use_remote_db(dataset: DotDict | Dataset, db_type: str, function_name: str, arguments: dict) -> Any:
    params = dataset.source_plugin_parameters or {}
    host = params.get("host", "")
    remote_dataset_id = params.get("dataset_id")
    access_token = params.get("access_token")
    url = host + "/data_backend/remote_db_access"
    data = {
        "dataset_id": remote_dataset_id,
        "access_token": access_token,
        "db_type": db_type,
        "function_name": function_name,
        "arguments": arguments,
    }
    body = json.dumps(data, cls=CustomJSONEncoder)
    result = requests.post(url, data=body, headers={"Content-Type": "application/json"})
    if db_type == "vector_search_engine" and function_name == "get_items_by_ids":
        return [DotDict(point) for point in result.json()["result"]]
    if db_type == "vector_search_engine" and function_name == "get_items_near_vector":
        return [DotDict(point) for point in result.json()["result"]]
    return result.json()["result"]
