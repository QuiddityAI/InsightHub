import os
from typing import Iterable

import requests

DATA_BACKEND_HOST = os.getenv("data_backend_host", "http://localhost:55123")

BACKEND_AUTHENTICATION_SECRET = os.getenv("BACKEND_AUTHENTICATION_SECRET", "not_set")


def get_data_backend_health():
    url = DATA_BACKEND_HOST + "/data_backend/health"
    headers = {
        "Authorization": f"{BACKEND_AUTHENTICATION_SECRET}",
    }
    result = requests.get(url, timeout=0.1, headers=headers)
    return result.status_code == 200


def get_data_backend_database_health():
    url = DATA_BACKEND_HOST + "/data_backend/db_health"
    headers = {
        "Authorization": f"{BACKEND_AUTHENTICATION_SECRET}",
    }
    result = requests.get(url, timeout=0.7, headers=headers)
    return result.status_code == 200


def get_item_by_id(dataset_id: int, item_id: str, fields: Iterable[str]):
    url = DATA_BACKEND_HOST + f"/data_backend/document/details_by_id"
    data = {
        "dataset_id": dataset_id,
        "item_id": item_id,
        "fields": fields,
    }
    result = requests.post(url, json=data)
    result.raise_for_status()
    return result.json()


def delete_dataset_content(dataset_id: int):
    url = DATA_BACKEND_HOST + f"/data_backend/delete_dataset_content"
    data = {
        "dataset_id": dataset_id,
    }
    headers = {
        "Authorization": f"{BACKEND_AUTHENTICATION_SECRET}",
    }
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
