
import logging
from typing import Iterable
import requests
import os
import json
import base64

import cachetools.func

from ..utils.dotdict import DotDict
from ..utils.custom_json_encoder import CustomJSONEncoder


backend_url = os.getenv("organization_backend_host", "http://localhost:55125")

BACKEND_AUTHENTICATION_SECRET = os.getenv("BACKEND_AUTHENTICATION_SECRET", "not_set")

# create requests session with BACKEND_AUTHENTICATION_SECRET as header:
django_client = requests.Session()
django_client.headers.update({'Authorization': BACKEND_AUTHENTICATION_SECRET})


@cachetools.func.ttl_cache(maxsize=128, ttl=10)  # seconds
def get_dataset(dataset_id: int) -> DotDict:
    url = backend_url + '/org/data_map/dataset'
    data = {
        'dataset_id': dataset_id,
    }
    result = django_client.post(url, json=data)
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
    result = django_client.post(url, json=body)
    return result.json()


def get_stored_map_data(map_id: str) -> dict | None:
    url = backend_url + '/org/data_map/stored_map_data'
    data = {
        'map_id': map_id,
    }
    result = django_client.post(url, json=data)
    if result.status_code == 200:
        map_data = json.loads(base64.b64decode(result.content.decode()))
        # during serialization, the keys are converted to strings, so we need to convert them back to integers
        for dataset_id_str in map_data['results']['slimmed_items_per_dataset'].keys():
            map_data['results']['slimmed_items_per_dataset'][int(dataset_id_str)] = map_data['results']['slimmed_items_per_dataset'].pop(dataset_id_str)
        return map_data
    else:
        return None


def get_collection(collection_id: int) -> DotDict | None:
    url = backend_url + '/org/data_map/get_collection'
    data = {
        'collection_id': collection_id,
    }
    result = django_client.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find collection: " + str(collection_id))
        return None
    return DotDict(result.json())


def get_collection_items(collection_id: int, class_name: str, field_type: str | None = None, is_positive: bool | None = None,
                         include_column_data: bool = False) -> list[dict]:
    url = backend_url + '/org/data_map/get_collection_items'
    data = {
        'collection_id': collection_id,
        'class_name': class_name,
        'type': field_type,
        'is_positive': is_positive,
        'include_column_data': include_column_data,
    }
    result = django_client.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find collection items")
        return []
    return result.json()


def add_item_to_collection(collection_id: int, class_name: str, is_positive: bool,
                           field_type: str, value: str | None, dataset_id: int | None, item_id: str | None,
                           weight: float | None) -> dict | None:
    url = backend_url + '/org/data_map/add_item_to_collection'
    data = {
        'collection_id': collection_id,
        'class_name': class_name,
        'is_positive': is_positive,
        'field_type': field_type,
        'value': value,
        'dataset_id': dataset_id,
        'item_id': item_id,
        'weight': weight if isinstance(weight, float) else 1.0,
    }
    result = django_client.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't add collection item")
        return None
    return result.json()


def get_trained_classifier(collection_id: int, class_name: str, embedding_space_identifier: int, include_vector: bool) -> DotDict:
    url = backend_url + '/org/data_map/get_trained_classifier'
    data = {
        'collection_id': collection_id,
        'class_name': class_name,
        'embedding_space_identifier': embedding_space_identifier,
        'include_vector': include_vector,
    }
    result = django_client.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't find classifier decision vector")
        return DotDict()
    return DotDict(result.json())


def set_trained_classifier(collection_id: int, class_name: str, embedding_space_identifier: int,
                           decision_vector: Iterable, highest_score: float | None, threshold: float | None,
                           metrics: dict) -> None:
    url = backend_url + '/org/data_map/set_trained_classifier'
    data = {
        'collection_id': collection_id,
        'class_name': class_name,
        'embedding_space_identifier': embedding_space_identifier,
        'decision_vector': decision_vector,
        'highest_score': highest_score,
        'threshold': threshold,
        'metrics': metrics,
    }
    result = django_client.post(url, json=data)
    if result.status_code != 204:
        logging.warning("Couldn't set trained classifier")
    return None


def get_generators() -> list[DotDict]:
    url = backend_url + '/org/data_map/get_generators'
    result = django_client.post(url)
    if result.status_code != 200:
        logging.warning("Couldn't get generators")
        return []
    return [DotDict(generator) for generator in result.json()]


def get_import_converter(import_converter_identifier: str) -> DotDict:
    url = backend_url + '/org/data_map/get_import_converter'
    data = {
        'identifier': import_converter_identifier,
    }
    result = django_client.post(url, json=data)
    return DotDict(result.json())


def get_export_converter(export_converter_identifier: str) -> DotDict:
    url = backend_url + '/org/data_map/get_export_converter'
    data = {
        'identifier': export_converter_identifier,
    }
    result = django_client.post(url, json=data)
    return DotDict(result.json())


def get_or_create_default_dataset(user_id: int, schema_identifier: str, organization_id: int) -> DotDict:
    url = backend_url + '/org/data_map/get_or_create_default_dataset'
    data = {
        'user_id': user_id,
        'schema_identifier': schema_identifier,
        'organization_id': organization_id,
    }
    result = django_client.post(url, json=data)
    return DotDict(result.json())


def get_related_collection_items(dataset_id: int, item_id: str, include_column_data: bool = False) -> list[dict]:
    url = backend_url + '/org/data_map/get_related_collection_items'
    data = {
        'dataset_id': dataset_id,
        'item_id': item_id,
        'include_column_data': include_column_data,
    }
    result = django_client.post(url, json=data)
    return result.json()


def answer_question_using_items(question: str, ds_and_item_ids: list[tuple]) -> dict:
    url = backend_url + '/org/data_map/answer_question_using_items'
    data = {
        'question': question,
        'ds_and_item_ids': ds_and_item_ids,
    }
    result = django_client.post(url, json=data)
    return result.json()


def track_service_usage(user_id: int, service_name: str, amount: float, cause: str) -> dict:
    url = backend_url + '/org/data_map/track_service_usage'
    data = {
        'user_id': user_id,
        'service_name': service_name,
        'amount': amount,
        'cause': cause,
    }
    result = django_client.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't track service usage")
    return result.json()


def get_service_usage(user_id: int, service_name: str) -> dict:
    url = backend_url + '/org/data_map/get_service_usage'
    data = {
        'user_id': user_id,
        'service_name': service_name,
    }
    result = django_client.post(url, json=data)
    if result.status_code != 200:
        logging.warning("Couldn't get service usage")
    return result.json()
