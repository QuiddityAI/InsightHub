import base64
import json
import logging
import os
from typing import Iterable

import requests

from data_map_backend.utils import DotDict
from legacy_backend.database_client.django_client import get_dataset
from legacy_backend.database_client.text_search_engine_client import (
    TextSearchEngineClient,
)
from legacy_backend.database_client.vector_search_engine_client import (
    VectorSearchEngineClient,
)
from legacy_backend.utils.custom_json_encoder import CustomJSONEncoder


def forward_local_db(params: DotDict):
    local_dataset = get_dataset(params.dataset_id)
    if params.db_type == "text_search_engine":
        search_engine_client = TextSearchEngineClient.get_instance()
        if params.function_name == "get_item_count":
            return search_engine_client.get_item_count(local_dataset)
        elif params.function_name == "get_items_by_ids":
            return search_engine_client.get_items_by_ids(local_dataset, **params.arguments)
        elif params.function_name == "get_search_results":
            return search_engine_client.get_search_results(local_dataset, **params.arguments)
    if params.db_type == "vector_search_engine":
        search_engine_client = VectorSearchEngineClient.get_instance()
        if params.function_name == "get_item_count":
            return search_engine_client.get_item_count(local_dataset, **params.arguments)
        elif params.function_name == "get_items_by_ids":
            result = search_engine_client.get_items_by_ids(local_dataset, **params.arguments)
            result = [{key: getattr(item, key, None) for key in ["id", "payload", "vector"]} for item in result]
            return result
        elif params.function_name == "get_items_near_vector":
            result = search_engine_client.get_items_near_vector(local_dataset, **params.arguments)
            result = [
                {key: getattr(item, key, None) for key in ["id", "score", "payload", "vector"]} for item in result
            ]
            return result
