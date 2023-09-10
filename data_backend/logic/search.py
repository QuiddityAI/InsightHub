import json
import logging
from uuid import UUID
from functools import lru_cache

from utils.field_types import FieldType
from utils.collect_timings import Timings
from utils.dotdict import DotDict

from database_client.absclust_database_client import get_absclust_search_results, get_absclust_item_by_id, save_search_cache
from database_client.django_client import get_object_schema
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.object_storage_client import ObjectStorageEngineClient
from database_client.text_search_engine_client import TextSearchEngineClient

from logic.postprocess_search_results import enrich_search_results
from logic.generator_functions import get_generator_function

from database_client.django_client import get_object_schema


#@lru_cache()
def get_search_results(params_str: str, purpose: str) -> dict:
    timings = Timings()
    params = DotDict(json.loads(params_str))

    schema = get_object_schema(params.schema_id)

    if params.search.search_type == "external_input":
        if params.search.use_separate_queries:
            search_results = get_search_results_using_separate_queries(schema, params.search, timings)
        else:
            search_results = get_search_results_using_combined_query(schema, params.search, params.vectorize, purpose, timings)
    elif params.search.search_type == "cluster":
        search_results = get_search_results_for_cluster(schema, params.search, timings)
    elif params.search.search_type == "collection":
        search_results = get_search_results_matching_a_collection(schema, params.search, timings)
    elif params.search.search_type == "similar_to_item":
        search_results = get_search_results_similar_to_item(schema, params.search, timings)
    else:
        logging.error("Unsupported search type: " + params.search.search_type, timings)
        search_results = []

    result = {
        "items": search_results,
        "timings": timings.get_timestamps(),
        "rendering": schema.result_list_rendering,
    }
    return result


def get_search_results_using_combined_query(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    raw_query = search_settings.all_field_query
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([raw_query, limit, page is not None, schema]):
        raise ValueError("a parameter is missing")

    rendering = schema.result_list_rendering if purpose == "list" else schema.hover_label_rendering
    required_fields = rendering['required_fields']

    if purpose == "map" and not vectorize_settings.use_w2v_model and vectorize_settings.map_vector_field not in required_fields:
        required_fields.append(vectorize_settings.map_vector_field)

    if purpose == "map" and schema.thumbnail_image:
        required_fields.append(schema.thumbnail_image)

    if purpose == "map":
        # used for cluster titles and potentially w2v:
        # TODO: this may be slow, maybe use only subset for cluster titles?
        required_fields += schema.descriptive_text_fields

    required_fields = list(set(required_fields))

    or_queries = raw_query.split(" OR ")
    timings.log("preparation")

    # TODO: currently only first page is returned
    if schema.id == ABSCLUST_SCHEMA_ID:
        results =  get_absclust_search_results(raw_query, required_fields, limit)
        save_search_cache()
        return results

    result_sets: list[dict] = []
    for query in or_queries:
        text_fields = []
        for field in schema.object_fields.values():
            if not field.is_available_for_search:
                continue
            if field.field_type == FieldType.VECTOR and search_settings.combined_search_strategy in ["hybrid", "vector"]:
                results = get_vector_search_results(schema, field.identifier, query, required_fields=[], limit=limit, page=page)
                result_sets.append(results)
                timings.log("vector database query")
            elif field.field_type == FieldType.TEXT and search_settings.combined_search_strategy in ["hybrid", "fulltext"]:
                text_fields.append(field.identifier)
            else:
                continue
        if text_fields:
            results = get_fulltext_search_results(schema, text_fields, query, required_fields=['_id'], limit=limit, page=page)
            result_sets.append(results)
            timings.log("fulltext database query")

    total_items = result_sets[0] if result_sets else {}
    for result_set in result_sets[1:]:
        for item in result_set.values():
            if item['_id'] not in total_items:
                total_items[item['_id']] = item
            else:
                total_items[item['_id']]['_source_scores'] += (item['_source_scores'])
                total_items[item['_id']]['_source_types'] += (item['_source_types'])
                total_items[item['_id']]['_source_fields'] += (item['_source_fields'])
                total_items[item['_id']]['_source_queries'] += (item['_source_queries'])
                total_items[item['_id']]['_ranks'] += (item['_ranks'])

    # TODO: check how much faster it is to get partial results from search engines and only fill in missing fields
    # TODO: only fill in values for results that are higher ranked than "limit" (in case of oversampling)
    fill_in_details_from_object_storage(schema.id, total_items, required_fields)
    timings.log("getting full items from object storage")

    if purpose == "map" and not vectorize_settings.use_w2v_model:
        # filter out items without the necessary map vector field:
        logging.warning("Before filtering: " + str(len(total_items)))
        total_items = {key: total_items[key] for key in total_items if vectorize_settings.map_vector_field in total_items[key]}
        logging.warning("After filtering: " + str(len(total_items)))

    for item in total_items.values():
        item['_reciprocal_rank_score'] = sum([1.0 / rank for rank in item['_ranks']])

    if len(result_sets) > 1:
        for item in total_items.values():
            item['_score'] = item['_reciprocal_rank_score']
    else:
        for item in total_items.values():
            item['_score'] = item['_source_scores'][0]

    sorted_results = sorted(total_items.values(), key=lambda item: item['_reciprocal_rank_score'], reverse=True)
    timings.log("rank fusion and sorting")

    # search_results = enrich_search_results(search_results, query)
    # timings.log("enriching results")
    # -> replaced by context dependent generator (for important words per abstract and highlighting of words)

    return sorted_results[:limit]


def get_fulltext_search_results(schema: DotDict, text_fields: list[str], query: str, required_fields: list[str], limit: int, page: int):
    text_db_client = TextSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    search_result = text_db_client.get_search_results(schema.id, text_fields, criteria, query, "", page, limit, required_fields, highlights=True)
    items = {}
    for i, item in enumerate(search_result):
        items[item['_id']] = {
            '_id': item['_id'],
            '_source_scores': [item['_score']],
            '_source_types': ['fulltext'],
            '_source_fields': ['unknown'],  # TODO
            '_source_queries': [query],
            '_ranks': [i + 1],
            '_highlights': " ".join([" ".join(x) for x in item.get('highlight', {}).values()])
        }
    return items


ABSCLUST_SCHEMA_ID = 1


def get_vector_search_results(schema: DotDict, vector_field: str, query: str, required_fields: list[str], limit: int, page: int):
    generator = schema.object_fields[vector_field].generator
    generator_function = get_generator_function(generator.identifier, schema.object_fields[vector_field].generator_parameters)
    query_vector = generator_function([query])[0]

    vector_db_client = VectorSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    vector_search_result = vector_db_client.get_items_near_vector(schema.id, vector_field, query_vector, criteria, return_vectors=False, limit=limit)
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            '_id': item.id,
            '_source_scores': [item.score],
            '_source_types': ['vector'],
            '_source_fields': [vector_field],
            '_source_queries': [query],
            '_ranks': [i + 1],
        }

    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]

    return items


def fill_in_details_from_object_storage(schema_id:int, items: dict, required_fields: list[str]):
    object_storage_client = ObjectStorageEngineClient.get_instance()
    object_storage_result = object_storage_client.get_items_by_ids(schema_id, map(UUID, items.keys()), fields=required_fields)
    for result in object_storage_result:
        items[str(result['_id'])].update(result)


def get_search_results_using_separate_queries(schema, search_settings: DotDict, timings: Timings) -> list:
    return []


def get_search_results_for_cluster(schema, search_settings: DotDict, timings: Timings) -> list:
    return []


def get_search_results_similar_to_item(schema, search_settings: DotDict, timings: Timings) -> list:
    return []


def get_search_results_matching_a_collection(schema, search_settings: DotDict, timings: Timings) -> list:
    return []


@lru_cache
def get_document_details_by_id(schema_id: int, item_id: str, fields: tuple[str]):
    if schema_id == ABSCLUST_SCHEMA_ID:
        return get_absclust_item_by_id(item_id)

    object_storage_client = ObjectStorageEngineClient.get_instance()
    items = object_storage_client.get_items_by_ids(schema_id, [UUID(item_id)], fields=fields)
    if not items:
        return None

    return items[0]
