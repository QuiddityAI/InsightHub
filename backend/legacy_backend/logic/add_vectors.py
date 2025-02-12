import logging
import math
import time

import numpy as np

from data_map_backend.utils import DotDict
from legacy_backend.logic.extract_pipeline import get_pipeline_steps
from legacy_backend.logic.generate_missing_values import (
    generate_missing_values_for_given_elements,
)
from legacy_backend.logic.generator_functions import get_generator_function_from_field
from legacy_backend.logic.model_client import embedding_cache, save_embedding_cache
from legacy_backend.logic.search_common import get_required_fields
from legacy_backend.utils.field_types import FieldType


def add_missing_map_vectors(items: dict[str, dict], query, params: DotDict, map_data, dataset, timings):
    if not items:
        return
    map_data["progress"]["step_title"] = "Generating vectors"
    map_data["progress"]["total_steps"] = len(items)
    map_data["progress"]["current_step"] = 0

    map_vector_field = dataset.schema.object_fields[params.vectorize.map_vector_field]
    t1 = time.time()

    # try to get embeddings from cache:
    for item in items.values():
        if item.get(map_vector_field.identifier) is not None:
            continue
        cache_key = str(dataset.id) + item["_id"] + map_vector_field.identifier
        cached_embedding = embedding_cache.get(cache_key, None)
        if cached_embedding is not None:
            item[map_vector_field.identifier] = cached_embedding

    if not all([item.get(map_vector_field.identifier) is not None for item in items.values()]):
        # if some or all vectors are still missing, generate them:
        batch_size = 2048
        pipeline_steps, required_fields, _ = get_pipeline_steps(dataset, only_fields=[map_vector_field.identifier])
        available_fields = get_required_fields(dataset, params.vectorize, "map")
        missing_fields = required_fields - set(available_fields)
        if missing_fields:
            logging.warning(
                f"Some fields are missing in the search result data to generate missing vectors: {missing_fields}"
            )
        for batch_number in range(math.ceil(len(items) / batch_size)):
            elements = list(items.values())[batch_number * batch_size : (batch_number + 1) * batch_size]
            changed_fields = generate_missing_values_for_given_elements(pipeline_steps, elements)
            for i, item in enumerate(elements):
                if map_vector_field.identifier in changed_fields[i]:
                    cache_key = str(dataset.id) + item["_id"] + map_vector_field.identifier
                    embedding_cache[cache_key] = item[map_vector_field.identifier]
            map_data["progress"]["current_step"] = batch_number * batch_size
        save_embedding_cache()

    duration_per_item = (time.time() - t1) / len(items)
    timings.log(f"adding missing vectors ({duration_per_item * 1000:.1f} ms per item)")

    # check if scores need to be re-calculated:
    scores = [item.get("_score") for item in items.values()]
    if (
        query
        and map_vector_field.generator
        and map_vector_field.generator.input_type == FieldType.TEXT
        and (not all([score is not None for score in scores]) or np.min(scores) == np.max(scores))
    ):
        map_data["progress"]["step_title"] = "Generating scores"
        map_data["progress"]["total_steps"] = len(items)
        map_data["progress"]["current_step"] = 0

        generator_function = get_generator_function_from_field(map_vector_field)
        query_embedding = generator_function([[query]])[0]

        for i, item in enumerate(items.values()):
            item_embedding = item[map_vector_field.identifier]
            item["_score"] = np.dot(query_embedding, item_embedding)

            map_data["progress"]["current_step"] = i
        timings.log("adding scores")
