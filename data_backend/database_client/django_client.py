
import logging
from typing import Iterable
import requests
import os
import json
import base64

from utils.dotdict import DotDict
from utils.custom_json_encoder import CustomJSONEncoder


backend_url = os.getenv("organization_backend_host", "http://localhost:55125")


def get_dataset(dataset_id: int) -> DotDict:
    url = backend_url + '/org/data_map/dataset'
    data = {
        'dataset_id': dataset_id,
    }
    result = requests.post(url, json=data)
    return DotDict(result.json())


def add_stored_map(map_id, user_id, organization_id, name, display_name, map_data) -> dict:
    url = backend_url + '/org/data_map/add_stored_map'
    encoded_map_data = base64.b64encode(json.dumps(map_data, cls=CustomJSONEncoder).encode()).decode()
    logging.warning(f"storing map, size: {len(encoded_map_data) / 1024 / 1024} MB")
    body = {
        'user_id': user_id,
        'organization_id': organization_id,
        'name': name,
        'display_name': display_name,
        'map_id': map_id,
        'map_data': encoded_map_data,
    }
    result = requests.post(url, json=body)
    return result.json()


def get_stored_map_data(map_id: str) -> dict | None:
    url = backend_url + '/org/data_map/stored_map_data'
    data = {
        'map_id': map_id,
    }
    result = requests.post(url, json=data)
    if result.status_code == 200:
        map_data = json.loads(base64.b64decode(result.content.decode()))
        return map_data
    else:
        return None


def get_collection(collection_id: int) -> DotDict | None:
    url = backend_url + '/org/data_map/get_collection'
    data = {
        'collection_id': collection_id,
    }
    result = requests.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find collection: " + str(collection_id))
        return None
    return DotDict(result.json())


def get_collection_items(collection_id: int, class_name: str, field_type: str | None = None, is_positive: bool | None = None) -> list[dict]:
    url = backend_url + '/org/data_map/get_collection_items'
    data = {
        'collection_id': collection_id,
        'class_name': class_name,
        'type': field_type,
        'is_positive': is_positive,
    }
    result = requests.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find collection items")
        return []
    return result.json()


def get_trained_classifier(collection_id: int, class_name: str, embedding_space_id: int, include_vector: bool) -> DotDict:
    url = backend_url + '/org/data_map/get_trained_classifier'
    data = {
        'collection_id': collection_id,
        'class_name': class_name,
        'embedding_space_id': embedding_space_id,
        'include_vector': include_vector,
    }
    result = requests.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find classifier decision vector")
        return DotDict()
    return DotDict(result.json())


def set_trained_classifier(collection_id: int, class_name: str, embedding_space_id: int,
                           decision_vector: Iterable, highest_score: float | None, threshold: float | None,
                           metrics: dict) -> None:
    url = backend_url + '/org/data_map/set_trained_classifier'
    data = {
        'collection_id': collection_id,
        'class_name': class_name,
        'embedding_space_id': embedding_space_id,
        'decision_vector': decision_vector,
        'highest_score': highest_score,
        'threshold': threshold,
        'metrics': metrics,
    }
    result = requests.post(url, json=data)
    if result.status_code != 204:
        logging.warning("Couldn't set trained classifier")
    return None


def get_generators() -> list[DotDict]:
    url = backend_url + '/org/data_map/get_generators'
    result = requests.post(url)
    if result.status_code != 200:
        logging.warning("Couldn't get generators")
        return []
    return [DotDict(generator) for generator in result.json()]


def get_import_converter(import_converter_id: int) -> DotDict:
    url = backend_url + '/org/data_map/get_import_converter'
    data = {
        'import_converter_id': import_converter_id,
    }
    result = requests.post(url, json=data)
    return DotDict(result.json())
