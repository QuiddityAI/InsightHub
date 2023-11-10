import logging
import math
from typing import Iterable

import numpy as np

from utils.field_types import FieldType
from utils.collect_timings import Timings
from utils.dotdict import DotDict

from database_client.absclust_database_client import get_absclust_items_by_ids
from database_client.django_client import get_generators
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
                                 timings: Timings) -> tuple[list, dict]:
    score_info = get_score_curves_and_cut_sets(result_sets, search_settings, dataset)
    total_items = combine_result_sets_and_calculate_scores(result_sets, timings)
    sorted_complete_items = sort_items_and_complete_them(dataset, total_items, required_fields, limit, timings)
    return sorted_complete_items, score_info


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
                                 limit:int, timings:Timings) -> list[dict]:
    # TODO: check how much faster it is to get partial results from search engines and only fill in missing fields
    sorted_results = sorted(total_items.values(), key=lambda item: item['_reciprocal_rank_score'], reverse=True)
    sorted_results = sorted_results[:limit]
    timings.log("sort items")
    required_text_fields, required_vector_fields = separate_text_and_vector_fields(dataset, required_fields)
    fill_in_details_from_text_storage(dataset.id, sorted_results, required_text_fields)
    timings.log("getting actual data from text storage")
    if required_vector_fields:
        fill_in_vector_data(dataset.id, sorted_results, required_vector_fields)
        timings.log("getting vector data from vector DB")

    # search_results = enrich_search_results(search_results, query)
    # timings.log("enriching results")
    # -> replaced by context dependent generator (for important words per abstract and highlighting of words)

    return sorted_results


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


def get_fulltext_search_results(dataset: DotDict, text_fields: list[str], query: QueryInput,
                                required_fields: list[str], limit: int, page: int):
    text_db_client = TextSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    search_result = text_db_client.get_search_results(dataset.id, text_fields, criteria, query.positive_query_str, "", page, limit, required_fields, highlights=True)
    items = {}
    # TODO: required_fields is not implemented properly, the actual item data would be in item["_source"] and needs to be copied
    for i, item in enumerate(search_result):
        items[item['_id']] = {
            '_id': item['_id'],
            '_origins': [{'type': 'fulltext', 'field': 'unknown',
                          'query': query.positive_query_str, 'score': item['_score'], 'rank': i+1}],
            '_highlights': " ".join([" ".join(x) for x in item.get('highlight', {}).values()])
        }
    return items


def get_vector_search_results(dataset: DotDict, vector_field: str, query: QueryInput,
                              query_vector: list | None, required_fields: list[str],
                              limit: int, page: int, score_threshold: float | None):
    if query_vector is None:
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
            return {}

        if field.generator and field.generator.input_type == FieldType.TEXT \
            and not (suitable_generator and suitable_generator.is_preferred_for_search):
            generator_function = get_generator_function_from_field(dataset.object_fields[vector_field])
        else:
            generator_function = get_generator_function(suitable_generator.module, suitable_generator.default_parameters)

        query_vector = generator_function([[query.positive_query_str]])[0]
        if query.negative_query_str:
            negative_query_vector = generator_function([[query.negative_query_str]])[0]
            query_vector = query_vector - negative_query_vector

        # for image query:
        # TODO: same thing again, average both vectors

    vector_db_client = VectorSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    assert query_vector is not None
    vector_search_result = vector_db_client.get_items_near_vector(dataset.id, vector_field, query_vector,
                                                                  criteria, return_vectors=False, limit=limit,
                                                                  score_threshold=score_threshold) # type: ignore
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            '_id': item.id,
            '_origins': [{'type': 'vector', 'field': vector_field,
                          'query': query.positive_query_str, 'score': item.score, 'rank': i+1}],
        }

    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]

    return items


def get_vector_search_results_matching_collection(dataset: DotDict, vector_field: str,
                                                  positive_ids, negative_ids,
                                                  required_fields: list[str], limit: int, page: int,
                                                  score_threshold: float | None):
    vector_db_client = VectorSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    vector_search_result = vector_db_client.get_items_matching_collection(dataset.id, vector_field, positive_ids,
                                                                          negative_ids, criteria, return_vectors=False,
                                                                          limit=limit, score_threshold=score_threshold)
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


def fill_in_details_from_text_storage(dataset_id: int, items: list[dict], required_fields: list[str]):
    if not items:
        return
    ids = [item['_id'] for item in items]
    if dataset_id == ABSCLUST_DATASET_ID:
        full_items = get_absclust_items_by_ids(ids)
    else:
        search_engine_client = TextSearchEngineClient.get_instance()
        full_items = search_engine_client.get_items_by_ids(dataset_id, ids, fields=required_fields)
    for full_item in full_items:
        for item in items:
            if item['_id'] == full_item['_id']:
                item.update(full_item)
                break


def fill_in_vector_data(dataset_id: int, items: list[dict], required_vector_fields: list[str]):
    if not items or not required_vector_fields:
        return
    if dataset_id == ABSCLUST_DATASET_ID:
        return
    ids = [item['_id'] for item in items]
    vector_db_client = VectorSearchEngineClient.get_instance()
    for vector_field in required_vector_fields:
        results = vector_db_client.get_items_by_ids(dataset_id, ids, vector_field, return_vectors=True, return_payloads=False)
        for result in results:
            for item in items:
                if item['_id'] == result.id:
                    item[vector_field] = result.vector[vector_field]
                    break


def get_field_similarity_threshold(field, use_image_threshold: bool | None=None):
    if use_image_threshold is None:
        # if not determined by other means, use same type as this field:
        use_image_threshold = field.generator.input_type == FieldType.IMAGE if field.generator else False
    score_threshold = field.image_similarity_threshold if use_image_threshold else field.text_similarity_threshold
    return score_threshold
