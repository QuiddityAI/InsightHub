import os
from typing import Iterable

import requests


data_backend_url = os.getenv("data_backend_host", "http://localhost:55123")


def get_item_by_id(dataset_id: int, item_id: str, fields: Iterable[str]):
    url = data_backend_url + f'/data_backend/document/details_by_id'  # type: ignore
    data = {
        'dataset_id': dataset_id,
        'item_id': item_id,
        'fields': fields,
    }
    result = requests.post(url, json=data)
    return result.json()
