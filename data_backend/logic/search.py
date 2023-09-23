import copy
import json
import logging
from uuid import UUID
from functools import lru_cache

from utils.field_types import FieldType
from utils.collect_timings import Timings
from utils.dotdict import DotDict

from database_client.absclust_database_client import get_absclust_search_results, get_absclust_item_by_id, get_absclust_items_by_ids, save_search_cache
from database_client.django_client import get_object_schema, get_collection
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.object_storage_client import ObjectStorageEngineClient
from database_client.text_search_engine_client import TextSearchEngineClient

from logic.postprocess_search_results import enrich_search_results
from logic.generator_functions import get_generator_function_from_field
from logic.local_map_cache import local_maps

from database_client.django_client import get_object_schema


#@lru_cache()
def get_search_results(params_str: str, purpose: str, timings: Timings | None = None) -> dict:
    if timings is None:
        timings = Timings()
    params = DotDict(json.loads(params_str))

    schema = get_object_schema(params.schema_id)

    if params.search.search_type == "external_input":
        if params.search.use_separate_queries:
            search_results = get_search_results_using_separate_queries(schema, params.search, params.vectorize, purpose, timings)
        else:
            search_results = get_search_results_using_combined_query(schema, params.search, params.vectorize, purpose, timings)
    elif params.search.search_type == "cluster":
        search_results = get_search_results_for_cluster(schema, params.search, params.vectorize, purpose, timings)
    elif params.search.search_type == "collection":
        search_results = get_search_results_included_in_collection(schema, params.search, params.vectorize, purpose, timings)
    elif params.search.search_type == "recommended_for_collection":
        search_results = get_search_results_matching_a_collection(schema, params.search, params.vectorize, purpose, timings)
    elif params.search.search_type == "similar_to_item":
        search_results = get_search_results_similar_to_item(schema, params.search, params.vectorize, purpose, timings)
    else:
        logging.error("Unsupported search type: " + params.search.search_type)
        search_results = []

    result = {
        "items": search_results,
        "timings": timings.get_timestamps(),
        "rendering": schema.result_list_rendering,
    }
    return result


def _get_required_fields(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str):
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
    return required_fields


def get_search_results_using_combined_query(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    raw_query = search_settings.all_field_query
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([raw_query, limit, page is not None, schema]):
        raise ValueError("a parameter is missing")

    required_fields = _get_required_fields(schema, search_settings, vectorize_settings, purpose)

    or_queries = raw_query.split(" OR ")
    timings.log("search preparation")

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
                results = get_vector_search_results(schema, field.identifier, query, None, required_fields=[], limit=limit, page=page)
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

    total_items = _combine_result_sets_and_calculate_scores(result_sets, timings)

    return _get_complete_items_and_sort_them(schema, total_items, required_fields, vectorize_settings, purpose, timings)[:limit]


def _combine_result_sets_and_calculate_scores(result_sets: list[dict], timings: Timings):
    total_items = result_sets[0] if result_sets else {}
    for result_set in result_sets[1:]:
        for item in result_set.values():
            if item['_id'] not in total_items:
                total_items[item['_id']] = item
            else:
                total_items[item['_id']]['_origins'] += item['_origins']

    for item in total_items.values():
        item['_reciprocal_rank_score'] = sum([1.0 / origin['rank'] for origin in item['_origins']])

    if len(result_sets) > 1:
        for item in total_items.values():
            item['_score'] = item['_reciprocal_rank_score']
    else:
        for item in total_items.values():
            item['_score'] = item['_origins'][0]['score']
    timings.log("rank fusion")
    return total_items

def _get_complete_items_and_sort_them(schema:DotDict, total_items:dict, required_fields:list[str], vectorize_settings:DotDict, purpose:str, timings:Timings) -> list[dict]:
    # TODO: check how much faster it is to get partial results from search engines and only fill in missing fields
    # TODO: only fill in values for results that are higher ranked than "limit" (in case of oversampling)
    fill_in_details_from_object_storage(schema.id, total_items, required_fields)
    timings.log("getting full items from object storage")

    if purpose == "map" and not vectorize_settings.use_w2v_model and not schema.id == ABSCLUST_SCHEMA_ID:
        # filter out items without the necessary map vector field:
        logging.warning("Before filtering: " + str(len(total_items)))
        total_items = {key: total_items[key] for key in total_items if vectorize_settings.map_vector_field in total_items[key]}
        logging.warning("After filtering: " + str(len(total_items)))


    sorted_results = sorted(total_items.values(), key=lambda item: item['_reciprocal_rank_score'], reverse=True)
    timings.log("filtering and sorting")

    # search_results = enrich_search_results(search_results, query)
    # timings.log("enriching results")
    # -> replaced by context dependent generator (for important words per abstract and highlighting of words)

    return sorted_results


def get_fulltext_search_results(schema: DotDict, text_fields: list[str], query: str, required_fields: list[str], limit: int, page: int):
    text_db_client = TextSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    search_result = text_db_client.get_search_results(schema.id, text_fields, criteria, query, "", page, limit, required_fields, highlights=True)
    items = {}
    for i, item in enumerate(search_result):
        items[item['_id']] = {
            '_id': item['_id'],
            '_origins': [{'type': 'fulltext', 'field': 'unknown',
                          'query': query, 'score': item['_score'], 'rank': i+1}],
            '_highlights': " ".join([" ".join(x) for x in item.get('highlight', {}).values()])
        }
    return items


ABSCLUST_SCHEMA_ID = 1


def get_vector_search_results(schema: DotDict, vector_field: str, query_str: str, query_vector: list | None, required_fields: list[str], limit: int, page: int):
    if query_vector is None:
        generator_function = get_generator_function_from_field(schema.object_fields[vector_field])
        query_vector = generator_function([[query_str]])[0]

    vector_db_client = VectorSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    vector_search_result = vector_db_client.get_items_near_vector(schema.id, vector_field, query_vector, criteria, return_vectors=False, limit=limit) # type: ignore
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            '_id': item.id,
            '_origins': [{'type': 'vector', 'field': vector_field,
                          'query': query_str, 'score': item.score, 'rank': i+1}],
        }

    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]

    return items


def get_vector_search_results_matching_collection(schema: DotDict, vector_field: str, positive_ids, negative_ids, required_fields: list[str], limit: int, page: int):
    vector_db_client = VectorSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    vector_search_result = vector_db_client.get_items_matching_collection(schema.id, vector_field, positive_ids, negative_ids, criteria, return_vectors=False, limit=limit)
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            '_id': item.id,
            '_origins': [{'type': 'vector', 'field': vector_field,
                          'query': 'matching a collection', 'score': item.score, 'rank': i+1}],
        }
    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]
    return items


def fill_in_details_from_object_storage(schema_id:int, items: dict, required_fields: list[str]):
    if schema_id == ABSCLUST_SCHEMA_ID:
        full_items = get_absclust_items_by_ids(list(items.keys()))
        for full_item in full_items:
            for item in items.values():
                if item['_id'] == full_item['id']:
                    item.update(full_item)
                    break
        return

    object_storage_client = ObjectStorageEngineClient.get_instance()
    object_storage_result = object_storage_client.get_items_by_ids(schema_id, map(UUID, items.keys()), fields=required_fields)
    for result in object_storage_result:
        result['_id'] = str(result['_id'])  # MongoDB returns IDs as UUID objects, but it should be strings here
        items[result['_id']].update(result)


def get_search_results_using_separate_queries(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    return []


def get_search_results_for_cluster(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    origin_map_id: str = search_settings.cluster_origin_map_id
    cluster_id: int = search_settings.cluster_id

    if origin_map_id not in local_maps:
        # TODO: check persisted maps, too?
        # But the map should already be local if someone clicks on a cluster
        raise ValueError("Map ID not found")

    origin_map: dict = local_maps[origin_map_id]
    results_per_point: dict = origin_map['results']['per_point_data']

    item_ids = results_per_point['item_ids']
    cluster_ids = results_per_point['cluster_ids']

    cluster_item_ids = []
    for i in range(len(item_ids)):
        if cluster_ids[i] == cluster_id:
            cluster_item_ids.append(item_ids[i])

    total_items = {}
    for i, item_id in enumerate(cluster_item_ids):
        total_items[item_id] = copy.deepcopy(origin_map['results']['search_result_meta_information'][item_id])

    required_fields = _get_required_fields(schema, search_settings, vectorize_settings, purpose)
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    # TODO: use page
    return _get_complete_items_and_sort_them(schema, total_items, required_fields, vectorize_settings, purpose, timings)[:limit]


def get_search_results_similar_to_item(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    if schema.id == ABSCLUST_SCHEMA_ID:
        # similar item functionality doesn't work with AbsClust database as it doesn't contain vectors
        return []
    similar_to_item_id = search_settings.similar_to_item_id
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([similar_to_item_id is not None, limit, page is not None, schema]):
        raise ValueError("a parameter is missing")

    timings.log("search preparation")

    vector_fields = [field.identifier for field in schema.object_fields.values() if field.is_available_for_search and field.field_type == FieldType.VECTOR]

    object_storage_client = ObjectStorageEngineClient.get_instance()
    item = object_storage_client.get_items_by_ids(schema.id, [UUID(similar_to_item_id)], fields=vector_fields)[0]
    timings.log("getting original item")

    result_sets: list[dict] = []
    for field in vector_fields:
        query_vector = item[field]
        results = get_vector_search_results(schema, field, 'other item', query_vector, required_fields=[], limit=limit, page=page)
        result_sets.append(results)
        timings.log("vector database query")

    total_items = _combine_result_sets_and_calculate_scores(result_sets, timings)
    required_fields = _get_required_fields(schema, search_settings, vectorize_settings, purpose)
    return _get_complete_items_and_sort_them(schema, total_items, required_fields, vectorize_settings, purpose, timings)[:limit]


def get_search_results_matching_a_collection(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    collection_id = search_settings.collection_id
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([collection_id is not None, limit, page is not None, schema]):
        raise ValueError("a parameter is missing")

    collection = get_collection(collection_id)
    if not collection:
        raise ValueError("Couldn't find the collection:" + str(collection_id))
    timings.log("search preparation")

    vector_fields = [field for field in schema.object_fields.values() if field.is_available_for_search and field.field_type == FieldType.VECTOR]
    result_sets: list[dict] = []
    for field in vector_fields:
        results = get_vector_search_results_matching_collection(schema, field.identifier, collection.positive_ids, collection.negative_ids, required_fields=[], limit=limit, page=page)
        result_sets.append(results)
        timings.log("vector database query")

    total_items = _combine_result_sets_and_calculate_scores(result_sets, timings)
    required_fields = _get_required_fields(schema, search_settings, vectorize_settings, purpose)
    return _get_complete_items_and_sort_them(schema, total_items, required_fields, vectorize_settings, purpose, timings)[:limit]


def get_search_results_included_in_collection(schema, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    collection_id = search_settings.collection_id
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([collection_id is not None, limit, page is not None, schema]):
        raise ValueError("a parameter is missing")

    collection = get_collection(collection_id)
    if not collection:
        raise ValueError("Couldn't find the collection:" + str(collection_id))
    timings.log("search preparation")

    result_sets: list[dict] = []
    positive_set = {}
    for item_id in collection.positive_ids:
        positive_set[item_id] = {
            '_id': item_id,
            '_origins': [{'type': 'collection', 'field': 'positives',
                          'query': '', 'score': 1.0, 'rank': 1}],
        }
    result_sets.append(positive_set)
    negative_set = {}
    for item_id in collection.negative_ids:
        negative_set[item_id] = {
            '_id': item_id,
            '_origins': [{'type': 'collection', 'field': 'negatives',
                          'query': '', 'score': 0.0, 'rank': 1}],
        }
    result_sets.append(negative_set)
    timings.log("collect items")

    total_items = _combine_result_sets_and_calculate_scores(result_sets, timings)
    required_fields = _get_required_fields(schema, search_settings, vectorize_settings, purpose)
    return _get_complete_items_and_sort_them(schema, total_items, required_fields, vectorize_settings, purpose, timings)


def get_search_results_for_stored_map(map_data):
    timings = Timings()
    params = DotDict(map_data['parameters'])
    search_settings = params.search
    vectorize_settings = params.vectorize
    schema = get_object_schema(params.schema_id)
    purpose = 'list'
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([limit, page is not None, schema]):
        raise ValueError("a parameter is missing")

    search_result_meta_info = map_data['results']['search_result_meta_information']
    sorted_results = sorted(search_result_meta_info.values(), key=lambda item: item['_reciprocal_rank_score'], reverse=True)
    limited_search_result_meta_info = {item['_id']: item for item in sorted_results[:limit]}
    search_results = get_full_results_from_meta_info(schema, search_settings, vectorize_settings, limited_search_result_meta_info, purpose, timings)
    result = {
        "items": search_results,
        "timings": timings.get_timestamps(),
        "rendering": schema.result_list_rendering,
    }
    return result


def get_full_results_from_meta_info(schema, search_settings, vectorize_settings, search_result_meta_info, purpose: str, timings):
    required_fields = _get_required_fields(schema, search_settings, vectorize_settings, purpose)
    search_results = _get_complete_items_and_sort_them(schema, search_result_meta_info, required_fields, vectorize_settings, purpose, timings)
    return search_results


@lru_cache
def get_document_details_by_id(schema_id: int, item_id: str, fields: tuple[str]):
    if schema_id == ABSCLUST_SCHEMA_ID:
        return get_absclust_item_by_id(item_id)

    object_storage_client = ObjectStorageEngineClient.get_instance()
    items = object_storage_client.get_items_by_ids(schema_id, [UUID(item_id)], fields=fields)
    if not items:
        return None

    return items[0]


def get_item_count(schema_id: int):
    object_storage_client = ObjectStorageEngineClient.get_instance()
    try:
        count = object_storage_client.get_item_count(schema_id)
        return count
    except Exception as e:
        logging.error(e)
        return -1
    return items[0]


def get_random_item(schema_id: int):
    object_storage_client = ObjectStorageEngineClient.get_instance()
    try:
        item = object_storage_client.get_random_item(schema_id)
        return item
    except Exception as e:
        logging.error(e)
        return {}
