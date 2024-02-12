import copy
import json
import logging
from functools import lru_cache

from utils.field_types import FieldType
from utils.collect_timings import Timings
from utils.dotdict import DotDict

from database_client.absclust_database_client import get_absclust_search_results, get_absclust_item_by_id, save_search_cache
from database_client.django_client import get_dataset, get_classifier
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.text_search_engine_client import TextSearchEngineClient
from logic.local_map_cache import local_maps
from logic.search_common import QueryInput, get_required_fields, get_vector_search_results, \
    get_vector_search_results_matching_classifier, get_fulltext_search_results, \
    combine_and_sort_result_sets, sort_items_and_complete_them, get_field_similarity_threshold, \
    fill_in_vector_data

from database_client.django_client import get_dataset


ABSCLUST_DATASET_ID = 1


#@lru_cache()
def get_search_results(params_str: str, purpose: str, timings: Timings | None = None) -> dict:
    if timings is None:
        timings = Timings()
    params = DotDict(json.loads(params_str))

    all_results = []
    all_score_info = {}
    for dataset_id in params.dataset_ids:
        dataset = get_dataset(dataset_id)
        score_info = {}

        if params.search.search_type == "external_input":
            if params.search.use_separate_queries:
                search_results = get_search_results_using_separate_queries(dataset, params.search, params.vectorize, purpose, timings)
            else:
                search_results, score_info = get_search_results_using_combined_query(dataset, params.search, params.vectorize, purpose, timings)
        elif params.search.search_type == "cluster":
            search_results = get_search_results_for_cluster(dataset, params.search, params.vectorize, purpose, timings)
        elif params.search.search_type == "classifier":
            search_results = get_search_results_included_in_classifier(dataset, params.search, params.vectorize, purpose, timings)
        elif params.search.search_type == "recommended_for_classifier":
            search_results, score_info = get_search_results_matching_a_classifier(dataset, params.search, params.vectorize, purpose, timings)
        elif params.search.search_type == "similar_to_item":
            search_results, score_info = get_search_results_similar_to_item(dataset, params.search, params.vectorize, purpose, timings)
        elif params.search.search_type == "global_map":
            search_results, score_info = get_search_results_for_global_map(dataset, params.search, params.vectorize, purpose, timings)
        else:
            logging.error("Unsupported search type: " + params.search.search_type)
            search_results = []
        all_results += search_results
        all_score_info.update(score_info)

    result = {
        "items": all_results,
        "score_info": all_score_info,
        "timings": timings.get_timestamps(),
    }
    return result


def get_search_results_using_combined_query(dataset, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> tuple[list, dict]:
    raw_query = search_settings.all_field_query
    negative_query = search_settings.all_field_query_negative
    image_query = ""  # TODO: search_settings.all_field_image_url
    negative_image_query = ""  # TODO: search_settings.all_field_image_url_negative
    enabled_fields = dataset.default_search_fields
    if search_settings.separate_queries:
        enabled_fields = [field_identifier for field_identifier, field_settings in search_settings.separate_queries.items() if field_settings['use_for_combined_search']]
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([raw_query, limit, page is not None, dataset]):
        raise ValueError("a parameter is missing")

    required_fields = get_required_fields(dataset, vectorize_settings, purpose)

    timings.log("search preparation")

    # TODO: currently only first page is returned
    if dataset.id == ABSCLUST_DATASET_ID:
        results =  get_absclust_search_results(raw_query, required_fields, limit)
        save_search_cache()
        return results, {}

    queries = QueryInput.from_raw_query(raw_query, negative_query, image_query, negative_image_query)
    result_sets: list[dict] = []
    for query in queries:
        text_fields = []
        for field in dataset.object_fields.values():
            if not field.is_available_for_search or field.identifier not in enabled_fields:
                continue
            if field.field_type == FieldType.VECTOR:
                score_threshold = get_field_similarity_threshold(field, input_is_image=bool(query.positive_image_url or query.negative_image_url))
                score_threshold = score_threshold if search_settings.use_similarity_thresholds else None
                results = get_vector_search_results(dataset, field.identifier, query, None, required_fields=[],
                                                    internal_input_weight=search_settings.internal_input_weight,
                                                    limit=limit, page=page, score_threshold=score_threshold)
                result_sets.append(results)
                timings.log("vector database query")
            elif field.field_type == FieldType.TEXT:
                text_fields.append(field.identifier)
            else:
                continue
        if text_fields:
            results = get_fulltext_search_results(dataset, text_fields, query, required_fields=['_id'], limit=limit, page=page)
            result_sets.append(results)
            timings.log("fulltext database query")

    # TODO: boost fulltext search the more words with low document frequency appear in query?

    return combine_and_sort_result_sets(result_sets, required_fields, dataset, search_settings, limit, timings)


def get_search_results_using_separate_queries(dataset, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    return []


def get_search_results_for_cluster(dataset, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
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

    required_fields = get_required_fields(dataset, vectorize_settings, purpose)
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    # TODO: use page
    return sort_items_and_complete_them(dataset, total_items, required_fields, limit, timings)


def get_search_results_similar_to_item(dataset, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> tuple[list, dict]:
    if dataset.id == ABSCLUST_DATASET_ID:
        # similar item functionality doesn't work with AbsClust database as it doesn't contain vectors
        return [], {}
    similar_to_item_id = search_settings.similar_to_item_id
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([similar_to_item_id is not None, limit, page is not None, dataset]):
        raise ValueError("a parameter is missing")

    timings.log("search preparation")

    vector_fields = [field for field in dataset.object_fields.values() if field.identifier in dataset.default_search_fields and field.field_type == FieldType.VECTOR]

    search_engine_client = TextSearchEngineClient.get_instance()
    items = search_engine_client.get_items_by_ids(dataset.id, [similar_to_item_id], fields=[field.identifier for field in vector_fields])
    fill_in_vector_data(dataset.id, items, [field.identifier for field in vector_fields])
    item = items[0]
    timings.log("getting original item")

    result_sets: list[dict] = []
    for field in vector_fields:
        query_vector = item[field.identifier]
        score_threshold = get_field_similarity_threshold(field) if search_settings.use_similarity_thresholds else None
        results = get_vector_search_results(dataset, field.identifier, QueryInput(search_settings.all_field_query, search_settings.all_field_query_negative), query_vector, required_fields=[],
                                            internal_input_weight=search_settings.internal_input_weight,
                                            limit=limit, page=page, score_threshold=score_threshold)
        result_sets.append(results)
        timings.log("vector database query")

    required_fields = get_required_fields(dataset, vectorize_settings, purpose)
    return combine_and_sort_result_sets(result_sets, required_fields, dataset, search_settings, limit, timings)


def get_search_results_matching_a_classifier(dataset, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> tuple[list, dict]:
    classifier_id = search_settings.classifier_id
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([classifier_id is not None, limit, page is not None, dataset]):
        raise ValueError("a parameter is missing")

    classifier = get_classifier(classifier_id)
    if not classifier:
        raise ValueError("Couldn't find the classifier:" + str(classifier_id))
    timings.log("search preparation")

    vector_fields = [field for field in dataset.object_fields.values() if field.is_available_for_search and field.field_type == FieldType.VECTOR]
    result_sets: list[dict] = []
    for field in vector_fields:
        score_threshold = get_field_similarity_threshold(field) if search_settings.use_similarity_thresholds else None
        results = get_vector_search_results_matching_classifier(dataset, field.identifier, classifier.positive_ids,
                                                                classifier.negative_ids, required_fields=[],
                                                                limit=limit, page=page, score_threshold=score_threshold)
        result_sets.append(results)
        timings.log("vector database query")

    required_fields = get_required_fields(dataset, vectorize_settings, purpose)
    return combine_and_sort_result_sets(result_sets, required_fields, dataset, search_settings, limit, timings)


def get_search_results_included_in_classifier(dataset, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> list:
    classifier_id = search_settings.classifier_id
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([classifier_id is not None, limit, page is not None, dataset]):
        raise ValueError("a parameter is missing")

    classifier = get_classifier(classifier_id)
    if not classifier:
        raise ValueError("Couldn't find the classifier:" + str(classifier_id))
    timings.log("search preparation")

    total_items = {}
    for item_id in classifier.positive_ids:
        total_items[item_id] = {
            '_id': item_id,
            '_origins': [{'type': 'classifier', 'field': 'positives',
                          'query': '', 'score': 1.0, 'rank': 1}],
            '_score': 1.0,
            '_reciprocal_rank_score': 1.0,
        }
    for item_id in classifier.negative_ids:
        total_items[item_id] = {
            '_id': item_id,
            '_origins': [{'type': 'classifier', 'field': 'negatives',
                          'query': '', 'score': 0.0, 'rank': 1}],
            '_score': 0.0,
            '_reciprocal_rank_score': 0.0,
        }
    timings.log("collect items")

    required_fields = get_required_fields(dataset, vectorize_settings, purpose)
    return sort_items_and_complete_them(dataset, total_items, required_fields, limit, timings)


def get_search_results_for_stored_map(map_data):
    timings = Timings()
    params = DotDict(map_data['parameters'])
    search_settings = params.search
    vectorize_settings = params.vectorize
    dataset = get_dataset(params.dataset_ids[0])
    purpose = 'list'
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([limit, page is not None, dataset]):
        raise ValueError("a parameter is missing")

    search_result_meta_info = map_data['results']['search_result_meta_information']
    sorted_results = sorted(search_result_meta_info.values(), key=lambda item: item['_reciprocal_rank_score'], reverse=True)
    limited_search_result_meta_info = {item['_id']: item for item in sorted_results[:limit]}
    search_results = get_full_results_from_meta_info(dataset, vectorize_settings, limited_search_result_meta_info, purpose, timings)
    result = {
        "items": search_results,
        "timings": timings.get_timestamps(),
    }
    return result


def get_search_results_for_global_map(dataset, search_settings: DotDict, vectorize_settings: DotDict, purpose: str, timings: Timings) -> tuple[list, dict]:
    limit = search_settings.result_list_items_per_page if purpose == "list" else search_settings.max_items_used_for_mapping
    page = search_settings.result_list_current_page if purpose == "list" else 0
    if not all([limit, page is not None, dataset]):
        raise ValueError("a parameter is missing")

    timings.log("search preparation")

    search_engine_client = TextSearchEngineClient.get_instance()
    search_result = search_engine_client.get_random_items(dataset.id, limit, [])
    items = {}
    for i, item in enumerate(search_result):
        items[item['_id']] = {
            '_id': item['_id'],
            '_origins': [{'type': 'random_sample', 'field': 'unknown',
                          'query': 'random sample', 'score': item['_score'], 'rank': i+1}],
        }
    result_sets: list[dict] = [items]

    required_fields = get_required_fields(dataset, vectorize_settings, purpose)
    return combine_and_sort_result_sets(result_sets, required_fields, dataset, search_settings, limit, timings)


def get_full_results_from_meta_info(dataset, vectorize_settings, search_result_meta_info: dict, purpose: str, timings) -> list[dict]:
    required_fields = get_required_fields(dataset, vectorize_settings, purpose)
    search_results: list[dict] = sort_items_and_complete_them(dataset, search_result_meta_info, required_fields, len(search_result_meta_info), timings)
    return search_results


@lru_cache
def get_document_details_by_id(dataset_id: int, item_id: str, fields: tuple[str]):
    if dataset_id == ABSCLUST_DATASET_ID:
        return get_absclust_item_by_id(item_id)

    search_engine_client = TextSearchEngineClient.get_instance()
    items = search_engine_client.get_items_by_ids(dataset_id, [item_id], fields=fields)
    if not items:
        return None

    return items[0]


def get_item_count(dataset_id: int) -> int:
    search_engine_client = TextSearchEngineClient.get_instance()
    try:
        count = search_engine_client.get_item_count(dataset_id)
        return count
    except Exception as e:
        logging.error(e)
        return 0


def get_items_having_value_count(dataset_id: int, field: str) -> int:
    dataset = get_dataset(dataset_id)
    if dataset.object_fields[field].field_type == FieldType.VECTOR:
        vector_db_client = VectorSearchEngineClient.get_instance()
        return vector_db_client.get_item_count(dataset_id, field)
    else:
        search_engine_client = TextSearchEngineClient.get_instance()
        try:
            count = search_engine_client.get_item_count(dataset_id)
            return count - search_engine_client.get_all_items_with_missing_field_count(dataset_id, field)
        except Exception as e:
            logging.error(e)
            return 0


def get_random_items(dataset_id: int, count: int) -> list[dict]:
    search_engine_client = TextSearchEngineClient.get_instance()
    try:
        items = search_engine_client.get_random_items(dataset_id, count)
        return items
    except Exception as e:
        logging.error(e)
        return []
