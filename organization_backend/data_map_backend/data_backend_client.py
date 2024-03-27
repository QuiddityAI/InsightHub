import os
from typing import Iterable

import requests


data_backend_url = os.getenv("data_backend_host", "http://localhost:55123")


def get_item_by_id(dataset_id: int, item_id: str, fields: Iterable[str]):
    url = data_backend_url + f'/data_backend/document/details_by_id'
    data = {
        'dataset_id': dataset_id,
        'item_id': item_id,
        'fields': fields,
    }
    result = requests.post(url, json=data)
    result.raise_for_status()
    return result.json()


def get_question_context(search_settings: dict):
    url = data_backend_url + f'/data_backend/question_context'
    data = {
        'search_settings': search_settings,
    }
    result = requests.post(url, json=data)
    result.raise_for_status()
    return result.json()['context']


def delete_dataset_content(dataset_id: int):
    url = data_backend_url + f'/data_backend/delete_dataset_content'
    data = {
        'dataset_id': dataset_id,
    }
    response = requests.post(url, json=data)
    response.raise_for_status()
