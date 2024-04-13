import logging
import math
import copy
from typing import Iterable
from functools import lru_cache
import json

import numpy as np

from utils.field_types import FieldType
from utils.collect_timings import Timings
from utils.dotdict import DotDict
from utils.source_plugin_types import SourcePlugin

from api_clients.old_absclust_database_client import get_absclust_items_by_ids, get_absclust_item_by_id
from database_client.django_client import get_generators, get_dataset
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.text_search_engine_client import TextSearchEngineClient

from logic.postprocess_search_results import enrich_search_results
from logic.generator_functions import get_generator_function_from_field, get_generator_function
from logic.autocut import get_number_of_useful_items

from utils.helpers import normalize_array


ABSCLUST_DATASET_ID = 1


class QueryInput(object):
    def __init__(self, positive_query_str: str, negative_query_str: str = "",
                 positive_image_url: str = "", negative_image_url: str = "") -> None:
        self.positive_query_str = positive_query_str
        self.negative_query_str = negative_query_str
        self.positive_image_url = positive_image_url
        self.negative_image_url = negative_image_url

    @staticmethod
    def from_raw_query(raw_query: str, negative_query_str: str, positive_image_url: str,
                       negative_image_url: str) -> list['QueryInput']:
        or_queries = raw_query.split(" OR ")
        queries = []
        for query in or_queries:
            queries.append(QueryInput(query, negative_query_str, positive_image_url, negative_image_url))
        return queries


def combine_and_sort_result_sets(result_sets: list[dict], required_fields: list[str],
                                 dataset: DotDict, search_settings: DotDict, limit: int,
                                 timings: Timings) -> tuple[list, dict, dict]:
    score_info = get_score_curves_and_cut_sets(result_sets, search_settings, dataset)
    total_items = combine_result_sets_and_calculate_scores(result_sets, timings)
    sorted_ids, full_items = sort_items_and_complete_them(dataset, total_items, required_fields, limit, timings)
    return sorted_ids, full_items, score_info


def get_score_curves_and_cut_sets(result_sets: list[dict], search_settings: DotDict, dataset: DotDict) -> dict:
    score_info = {}
    for result_set in result_sets:
        if not result_set:
            continue
        sorted_items = sorted(result_set.values(), key=lambda item: item['_origins'][0]['score'], reverse=True)
        example_origin = sorted_items[0]['_origins'][0]
        scores = [item['_origins'][0]['score'] for item in sorted_items]
        normalized_scores = normalize_array(np.array(scores)).tolist()
        cutoff_index = len(sorted_items)  # no cutoff by default
        title = f"{example_origin['type']}, {example_origin['field']}, {example_origin['query']}"
        positive_examples = []
        negative_examples = []
        reason = "no cutoff"
        if search_settings.use_autocut:
            useful_items_info = get_number_of_useful_items(scores, search_settings.autocut_min_results,
                                                      search_settings.autocut_strategy,
                                                      search_settings.autocut_min_score,
                                                      search_settings.autocut_max_relative_decline)
            cutoff_index = useful_items_info["count"]
            reason = useful_items_info["reason"]
            if cutoff_index != len(sorted_items):
                # TODO: there might be a better way to remove the cut items from the dictionary
                # result_set.clear()
                # for item in sorted_items[:cutoff_index]:
                #     result_set[item['_id']] = item
                positive_examples = [sorted_items[max(0, cutoff_index - 5)]['_id'],
                                     sorted_items[max(0, cutoff_index - 2)]['_id']]
                negative_examples = [sorted_items[min(len(sorted_items) - 1, cutoff_index + 5)]['_id'],
                                     sorted_items[min(len(sorted_items) - 1, cutoff_index + 2)]['_id']]
        score_info[title] = {'scores': normalized_scores, 'cutoff_index': cutoff_index, "reason": reason,
                             'max_score': max(scores), 'min_score': min(scores),
                             'positive_examples': positive_examples, 'negative_examples': negative_examples}

    # using new difference-to-top-results metric:
    # for result_set in result_sets:
    #     sorted_items = sorted(result_set.values(), key=lambda item: item['_origins'][0]['score'], reverse=True)
    #     example_origin = sorted_items[0]['_origins'][0]
    #     if example_origin["type"] != "vector":
    #         # the difference-to-top-results score only makes sense for vector results
    #         continue
    #     vector_field = example_origin["field"]
    #     fill_in_details_from_object_storage(dataset.id, sorted_items, [vector_field])
    #     top_n = 15
    #     top_items = sorted_items[:top_n]
    #     top_n_vector_average = np.mean([item[vector_field] for item in top_items], axis=0)
    #     # TODO: does np.dot work for non-normalized vectors? better use eucledian distance?
    #     scores = [np.dot(item[vector_field], top_n_vector_average) for item in sorted_items]
    #     for i in range(len(scores)):
    #         sorted_items[i]['_score'] = scores[i]
    #     sorted_items = sorted(sorted_items, key=lambda item: item['_score'], reverse=True)
    #     scores = [item['_score'] for item in sorted_items]
    #     normalized_scores = normalize_array(np.array(scores)).tolist()
    #     cutoff_index = len(sorted_items)  # no cutoff by default
    #     title = f"diff-to-top, {example_origin['type']}, {example_origin['field']}"
    #     positive_examples = []
    #     negative_examples = []
    #     reason = "no cutoff"
    #     if search_settings.use_autocut:
    #         useful_items_info = get_number_of_useful_items(scores, search_settings.autocut_min_results,
    #                                                   search_settings.autocut_strategy,
    #                                                   search_settings.autocut_min_score,
    #                                                   search_settings.autocut_max_relative_decline)
    #         cutoff_index = useful_items_info["count"]
    #         reason = useful_items_info["reason"]
    #         if cutoff_index != len(sorted_items):
    #             # TODO: there might be a better way to remove the cut items from the dictionary
    #             result_set.clear()
    #             for item in sorted_items[:cutoff_index]:
    #                 result_set[item['_id']] = item
    #             positive_examples = [sorted_items[max(0, cutoff_index - 5)]['_id'],
    #                                  sorted_items[max(0, cutoff_index - 2)]['_id']]
    #             negative_examples = [sorted_items[min(len(sorted_items) - 1, cutoff_index + 5)]['_id'],
    #                                  sorted_items[min(len(sorted_items) - 1, cutoff_index + 2)]['_id']]
    #     score_info[title] = {'scores': normalized_scores, 'cutoff_index': cutoff_index, "reason": reason,
    #                          'max_score': max(scores), 'min_score': min(scores),
    #                          'positive_examples': positive_examples, 'negative_examples': negative_examples}
    return score_info


def combine_result_sets_and_calculate_scores(result_sets: list[dict], timings: Timings):
    total_items = result_sets[0] if result_sets else {}
    for result_set in result_sets[1:]:
        for item in result_set.values():
            if item['_id'] not in total_items:
                total_items[item['_id']] = item
            else:
                total_items[item['_id']]['_origins'] += item['_origins']
                if '_relevant_parts' in item:
                    if '_relevant_parts' not in total_items[item['_id']]:
                        total_items[item['_id']]['_relevant_parts'] = []
                    total_items[item['_id']]['_relevant_parts'] += item['_relevant_parts']

    for item in total_items.values():
        item['_reciprocal_rank_score'] = sum([1.0 / origin['rank'] for origin in item['_origins']])

    if len(result_sets) > 1:
        for item in total_items.values():
            item['_score'] = math.sqrt(item['_reciprocal_rank_score'])  # making the score scale linear again
    else:
        for item in total_items.values():
            item['_score'] = item['_origins'][0]['score']
    timings.log("rank fusion")
    return total_items


def sort_items_and_complete_them(dataset:DotDict, total_items:dict, required_fields:list[str],
                                 limit:int, timings:Timings) -> tuple[list[str], dict[str, dict]]:
    # TODO: check how much faster it is to get partial results from search engines and only fill in missing fields
    sorted_ids = sorted(total_items.keys(), key=lambda id: total_items[id]['_reciprocal_rank_score'], reverse=True)
    for id_to_remove in sorted_ids[limit:]:
        del total_items[id_to_remove]
    sorted_ids = sorted_ids[:limit]
    timings.log("sort items")
    required_text_fields, required_vector_fields = separate_text_and_vector_fields(dataset, required_fields)
    fill_in_details_from_text_storage(dataset, total_items, required_text_fields)
    timings.log("getting actual data from text storage")
    if required_vector_fields:
        fill_in_vector_data(dataset, total_items, required_vector_fields)
        timings.log("getting vector data from vector DB")

    # search_results = enrich_search_results(search_results, query)
    # timings.log("enriching results")
    # -> replaced by context dependent generator (for important words per abstract and highlighting of words)

    return sorted_ids, total_items


def get_required_fields(dataset, vectorize_settings: DotDict, purpose: str):
    rendering = dataset.result_list_rendering if purpose == "list" else dataset.hover_label_rendering
    required_fields = rendering['required_fields']

    if purpose == "map" and vectorize_settings.map_vector_field \
        and vectorize_settings.map_vector_field != "w2v_vector" \
        and vectorize_settings.map_vector_field not in required_fields:
        required_fields.append(vectorize_settings.map_vector_field)

    if purpose == "map" and dataset.thumbnail_image:
        required_fields.append(dataset.thumbnail_image)

    if purpose == "map":
        # used for cluster titles and potentially w2v:
        # TODO: this may be slow, maybe use only subset for cluster titles?
        required_fields += dataset.descriptive_text_fields
        required_fields += dataset.get("statistics", {}).get("required_fields", [])

    required_fields = list(set(required_fields))
    return required_fields


def separate_text_and_vector_fields(dataset: DotDict, fields: Iterable[str]):
    vector_fields = []
    text_felds = []
    for field in fields:
        if dataset.object_fields[field].field_type == FieldType.VECTOR:
            vector_fields.append(field)
        else:
            text_felds.append(field)
    return text_felds, vector_fields


def get_fulltext_search_results(dataset: DotDict, text_fields: list[str], query: QueryInput, filters: list[dict],
                                required_fields: list[str], limit: int, page: int,
                                use_bolding_in_highlights: bool = True):
    text_db_client = TextSearchEngineClient.get_instance()
    search_result, total_matches = text_db_client.get_search_results(dataset.actual_database_name, text_fields, filters, query.positive_query_str, "", page, limit, required_fields, highlights=True, use_bolding_in_highlights=use_bolding_in_highlights)
    items = {}
    # TODO: required_fields is not implemented properly, the actual item data would be in item["_source"] and needs to be copied
    ignored_keyword_highlight_fields = dataset.defaults.ignored_keyword_highlight_fields or []
    for i, item in enumerate(search_result):
        items[item['_id']] = {
            '_id': item['_id'],
            '_dataset_id': dataset.id,
            '_origins': [{'type': 'fulltext', 'field': 'unknown',
                          'query': query.positive_query_str, 'score': item['_score'], 'rank': i+1}],
            '_relevant_parts': [{'origin': 'keyword_search', 'field': field_name, 'index': None, 'value': " [...] ".join(highlights)} for field_name, highlights in item.get('highlight', {}).items() if field_name not in ignored_keyword_highlight_fields]
        }
    return items, total_matches


def get_suitable_generator(dataset, vector_field: str):
    generators: list[DotDict] = get_generators()
    field = dataset.object_fields[vector_field]
    embedding_space_id = field.generator.embedding_space.id if field.generator else field.embedding_space.id

    # for text query:
    suitable_generator = None
    for generator in generators:
        if generator.embedding_space and generator.embedding_space.id == embedding_space_id \
            and generator.input_type == FieldType.TEXT:
            suitable_generator = generator

    if not suitable_generator:
        return None

    if field.generator and field.generator.input_type == FieldType.TEXT \
        and not (suitable_generator and suitable_generator.is_preferred_for_search):
        generator_function = get_generator_function_from_field(dataset.object_fields[vector_field], always_return_single_value_per_item=True)
    else:
        generator_function = get_generator_function(suitable_generator.module, suitable_generator.default_parameters, False)
    return generator_function


def get_vector_search_results(dataset: DotDict, vector_field: str, query: QueryInput,
                              query_vector: list | None, filters: list[dict] | None, required_fields: list[str],
                              internal_input_weight: float,
                              limit: int, page: int, score_threshold: float | None, max_sub_items: int | None = 1) -> dict[str, dict]:

    positive_query_vector = None
    negative_query_vector = None
    if query.positive_query_str or query.negative_query_str:
        generator_function = get_suitable_generator(dataset, vector_field)
        if not generator_function:
            return {}
        if query.positive_query_str:
            positive_query_vector = generator_function([[query.positive_query_str]])[0]
        if query.negative_query_str:
            negative_query_vector = generator_function([[query.negative_query_str]])[0]

        # for image query:
        # TODO: same thing again, average both vectors

    if query_vector is None and positive_query_vector is None:
        # search using only negative query isn't supported at the moment
        return {}
    if query_vector is None:
        query_vector = positive_query_vector
    elif positive_query_vector is not None:
        assert query_vector is not None
        query_vector = internal_input_weight * np.array(query_vector) + (1.0 - internal_input_weight) * positive_query_vector
    if negative_query_vector is not None:
        query_vector = query_vector - negative_query_vector * (1.0 - internal_input_weight)

    vector_db_client = VectorSearchEngineClient.get_instance()
    assert query_vector is not None
    is_array_field = dataset.object_fields[vector_field].is_array
    array_source_field = dataset.object_fields[vector_field].source_fields[0] if is_array_field and dataset.object_fields[vector_field].source_fields else None
    vector_search_result = vector_db_client.get_items_near_vector(dataset.actual_database_name, vector_field, query_vector,
                                                                  filters, return_vectors=False, limit=limit,
                                                                  score_threshold=score_threshold, is_array_field=is_array_field,
                                                                  max_sub_items=max_sub_items or 1) # type: ignore
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            '_id': item.id,
            '_dataset_id': dataset.id,
            '_origins': [{'type': 'vector', 'field': vector_field,
                          'query': query.positive_query_str, 'score': item.score, 'rank': i+1}],
        }
        if is_array_field:
            items[item.id]['_relevant_parts'] = [{'origin': 'vector_array', 'field': array_source_field, 'index': item.array_index}]

    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]

    return items


def get_vector_search_results_matching_collection(dataset: DotDict, vector_field: str,
                                                  positive_ids, negative_ids,
                                                  required_fields: list[str], limit: int, page: int,
                                                  score_threshold: float | None) -> dict[str, dict]:
    vector_db_client = VectorSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    vector_search_result = vector_db_client.get_items_matching_collection(dataset.actual_database_name, vector_field, positive_ids,
                                                                          negative_ids, criteria, return_vectors=False,
                                                                          limit=limit, score_threshold=score_threshold)
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            '_id': item.id,
            '_dataset_id': dataset.id,
            '_origins': [{'type': 'vector', 'field': vector_field,
                          'query': 'matching a collection', 'score': item.score, 'rank': i+1}],
        }
    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]
    return items


def fill_in_details_from_text_storage(dataset: DotDict, items: dict[str, dict], required_fields: list[str]):
    if not items:
        return
    if dataset.source_plugin != SourcePlugin.INTERNAL_OPENSEARCH_QDRANT:
        return
    if all(all(field in item for field in required_fields) for item in items.values()):
        # all required fields are already present
        return
    ids = list(items.keys())
    if dataset.id == ABSCLUST_DATASET_ID:
        full_items = get_absclust_items_by_ids(ids)
    else:
        search_engine_client = TextSearchEngineClient.get_instance()
        full_items = search_engine_client.get_items_by_ids(dataset.actual_database_name, ids, fields=required_fields)
    for full_item in full_items:
        items[full_item['_id']].update(full_item)


def fill_in_vector_data_list(dataset: DotDict, items: list[dict], required_vector_fields: list[str]):
    items_by_id = {item['_id']: item for item in items}
    fill_in_vector_data(dataset, items_by_id, required_vector_fields)


def fill_in_vector_data(dataset: DotDict, items: dict[str, dict], required_vector_fields: list[str]):
    if not items or not required_vector_fields:
        return
    if dataset.source_plugin != SourcePlugin.INTERNAL_OPENSEARCH_QDRANT:
        return
    if all(all(field in item for field in required_vector_fields) for item in items.values()):
        # all required fields are already present
        return
    if dataset.id == ABSCLUST_DATASET_ID:
        return
    ids = list(items.keys())
    vector_db_client = VectorSearchEngineClient.get_instance()
    for vector_field in required_vector_fields:
        is_array_field = dataset.object_fields[vector_field].is_array
        results = vector_db_client.get_items_by_ids(dataset.actual_database_name, ids, vector_field, is_array_field, return_vectors=True, return_payloads=False)
        for result in results:
            items[result.id][vector_field] = result.vector[vector_field]


def get_field_similarity_threshold(field: DotDict, input_is_image: bool | None=None):
    if input_is_image is None:
        # if not determined by other means, use same type as this field:
        input_is_image = field.generator.input_type == FieldType.IMAGE if field.generator else False
    score_threshold = field.image_similarity_threshold if input_is_image else field.text_similarity_threshold
    if score_threshold is None and field.generator:
        score_threshold = field.generator.image_similarity_threshold if input_is_image else field.generator.text_similarity_threshold
    return score_threshold


def get_relevant_parts_of_item_using_query_vector(dataset: DotDict, item_id: str, vector_field: str,
                           query_vector: list, score_threshold: float | None = None,
                           limit: int = 5, min_results: int = 2) -> dict:
    vector_db_client = VectorSearchEngineClient.get_instance()
    vector_search_results = vector_db_client.get_best_sub_items(dataset.actual_database_name, vector_field, item_id, query_vector, score_threshold, limit, min_results)
    item = {
        '_id': item_id,
        '_dataset_id': dataset.id,
        '_origins': [{'type': 'vector', 'field': vector_field,
                    'query': 'unknown', 'score': max(*(item.score for item in vector_search_results), 0.0), 'rank': 1}],
    }
    array_source_field = dataset.object_fields[vector_field].source_fields[0] if dataset.object_fields[vector_field].source_fields else None
    item['_relevant_parts'] = [{'origin': 'vector_array', 'field': array_source_field, 'index': item.payload['array_index'], 'score': item.score} for item in vector_search_results]
    return item


def adapt_filters_to_dataset(filters: list[dict], dataset: DotDict):
    filters = copy.deepcopy(filters)
    additional_filters = []
    removed_filters = []
    for filter_ in filters:
        if filter_['field'] == '_descriptive_text_fields':
            for field in dataset.descriptive_text_fields:
                additional_filters.append({'field': field, 'value': filter_['value'], 'operator': filter_['operator']})
            removed_filters.append(filter_)
    filters.extend(additional_filters)
    for filter_ in filters:
        if filter_ in removed_filters:
            continue
        if filter_['field'] in dataset.object_fields:
            field = dataset.object_fields[filter_['field']]
            if field.field_type == FieldType.INTEGER:
                try:
                    filter_['value'] = int(filter_['value'])
                except ValueError:
                    logging.warning(f"Could not convert filter value '{filter_['value']}' to integer for field '{field.name}'")
                    removed_filters.append(filter_)
            elif field.field_type == FieldType.FLOAT:
                try:
                    filter_['value'] = float(filter_['value'])
                except ValueError:
                    logging.warning(f"Could not convert filter value '{filter_['value']}' to float for field '{field.name}'")
                    removed_filters.append(filter_)
    for filter_ in removed_filters:
        filters.remove(filter_)
    return filters


@lru_cache
def get_document_details_by_id(dataset_id: int, item_id: str, fields: tuple[str], relevant_parts: str | None=None, database_name: str | None = None) -> dict | None:
    if dataset_id == ABSCLUST_DATASET_ID:
        return get_absclust_item_by_id(item_id)

    if not database_name:
        dataset = get_dataset(dataset_id)
        database_name = dataset.actual_database_name
        assert database_name is not None
    if relevant_parts:
        relevant_parts = json.loads(relevant_parts)
        assert isinstance(relevant_parts, list)
        original_fields = fields
        for relevant_part in relevant_parts:
            if relevant_part.get('origin') == 'keyword_search':  # type: ignore
                # the relevant part comes from keyword search where the text is already present
                # so we don't need to fetch any source fields
                continue
            fields = tuple([*fields, relevant_part['field']])  # type: ignore
    search_engine_client = TextSearchEngineClient.get_instance()
    items = search_engine_client.get_items_by_ids(database_name, [item_id], fields=fields)
    if not items:
        return None
    item = items[0]
    item['_dataset_id'] = dataset_id

    if relevant_parts:
        for relevant_part in relevant_parts:
            if relevant_part['index'] is not None:  # type: ignore
                try:
                    relevant_part['value'] = item[relevant_part['field']][relevant_part['index']]  # type: ignore
                except (IndexError, KeyError):
                    relevant_part['value'] = None  # type: ignore
                relevant_part['array_size'] = len(item.get(relevant_part['field'], []))  # type: ignore
                if relevant_part['field'] not in original_fields:  # type: ignore
                    del item[relevant_part['field']]  # type: ignore
        item['_relevant_parts'] = relevant_parts
    return item
