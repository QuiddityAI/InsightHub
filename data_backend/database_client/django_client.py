
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


def add_stored_map(map_id, user_id, dataset_id, name, map_data) -> dict:
    url = backend_url + '/org/data_map/add_stored_map'
    encoded_map_data = base64.b64encode(json.dumps(map_data, cls=CustomJSONEncoder).encode()).decode()
    logging.warning(f"storing map, size: {len(encoded_map_data) / 1024 / 1024} MB")
    body = {
        'user_id': user_id,
        'dataset_id': dataset_id,
        'name': name,
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


def get_classifier(classifier_id: int) -> DotDict | None:
    url = backend_url + '/org/data_map/get_classifier'
    data = {
        'classifier_id': classifier_id,
    }
    result = requests.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find classifier: " + str(classifier_id))
        return None
    return DotDict(result.json())


def get_classifier_examples(classifier_id: int, class_name: str, field_type: str | None = None, is_positive: bool | None = None) -> list[dict]:
    url = backend_url + '/org/data_map/get_classifier_examples'
    data = {
        'classifier_id': classifier_id,
        'class_name': class_name,
        'type': field_type,
        'is_positive': is_positive,
    }
    result = requests.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find classifier examples")
        return []
    return result.json()


def get_classifier_decision_vector(classifier_id: int, class_name: str, embedding_space_id: int) -> dict:
    url = backend_url + '/org/data_map/get_classifier_decision_vector'
    data = {
        'classifier_id': classifier_id,
        'class_name': class_name,
        'embedding_space_id': embedding_space_id,
    }
    result = requests.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find classifier decision vector")
        return []
    return result.json()


def set_classifier_decision_vector(classifier_id: int, class_name: str, embedding_space_id: int, decision_vector: Iterable, metrics: dict) -> None:
    url = backend_url + '/org/data_map/set_classifier_decision_vector'
    data = {
        'classifier_id': classifier_id,
        'class_name': class_name,
        'embedding_space_id': embedding_space_id,
        'decision_vector': decision_vector,
        'metrics': metrics,
    }
    result = requests.post(url, json=data)
    if result.status_code != 204:
        logging.warning("Couldn't set classifier decision vector")
    return None


def get_generators() -> list[DotDict]:
    url = backend_url + '/org/data_map/get_generators'
    result = requests.post(url)
    if result.status_code != 200:
        logging.warning("Couldn't get generators")
        return []
    return [DotDict(generator) for generator in result.json()]
