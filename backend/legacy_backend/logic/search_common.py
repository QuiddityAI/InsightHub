import copy
import json
import logging
import math
from functools import lru_cache
from typing import Iterable, Literal

import cachetools.func
import numpy as np

from data_map_backend.models import Generator
from data_map_backend.utils import DotDict, pk_to_uuid_id
from data_map_backend.views.other_views import get_serialized_dataset_cached
from legacy_backend.api_clients import openalex_api
from legacy_backend.api_clients.cohere_reranking import get_reranking_results
from legacy_backend.database_client.django_client import get_related_collection_items
from legacy_backend.database_client.text_search_engine_client import (
    TextSearchEngineClient,
)
from legacy_backend.database_client.vector_search_engine_client import (
    VectorSearchEngineClient,
)
from legacy_backend.logic.autocut import get_number_of_useful_items
from legacy_backend.logic.generator_functions import (
    get_generator_function,
    get_generator_function_from_field,
)
from legacy_backend.logic.postprocess_search_results import enrich_search_results
from legacy_backend.utils.collect_timings import Timings
from legacy_backend.utils.field_types import FieldType
from legacy_backend.utils.helpers import normalize_array
from legacy_backend.utils.source_plugin_types import SourcePlugin


class QueryInput(object):
    def __init__(
        self,
        positive_query_str: str,
        negative_query_str: str = "",
        positive_image_url: str = "",
        negative_image_url: str = "",
    ) -> None:
        self.positive_query_str = positive_query_str
        self.negative_query_str = negative_query_str
        self.positive_image_url = positive_image_url
        self.negative_image_url = negative_image_url

    @staticmethod
    def from_raw_query(
        raw_query: str, negative_query_str: str, positive_image_url: str, negative_image_url: str
    ) -> list["QueryInput"]:
        or_queries = raw_query.split(" OR ")
        queries = []
        for query in or_queries:
            queries.append(QueryInput(query, negative_query_str, positive_image_url, negative_image_url))
        return queries


def combine_and_sort_result_sets(
    result_sets: list[dict],
    required_fields: list[str],
    dataset: DotDict,
    search_settings: DotDict,
    limit: int,
    timings: Timings,
) -> tuple[list, dict, dict]:
    score_info = get_score_curves_and_cut_sets(result_sets, search_settings, dataset)
    total_items = combine_result_sets_and_calculate_scores(result_sets, timings)
    sorted_ids, full_items = sort_items_and_complete_them(dataset, total_items, required_fields, limit, timings)
    return sorted_ids, full_items, score_info


def get_score_curves_and_cut_sets(result_sets: list[dict], search_settings: DotDict, dataset: DotDict) -> dict:
    score_info = {}
    for result_set in result_sets:
        if not result_set:
            continue
        sorted_items = sorted(result_set.values(), key=lambda item: item["_origins"][0]["score"], reverse=True)
        example_origin = sorted_items[0]["_origins"][0]
        scores = [item["_origins"][0]["score"] for item in sorted_items]
        normalized_scores = normalize_array(np.array(scores)).tolist()
        cutoff_index = len(sorted_items)  # no cutoff by default
        title = f"{example_origin['type']}, {example_origin['field']}, {example_origin['query']}"
        positive_examples = []
        negative_examples = []
        reason = "no cutoff"
        if search_settings.use_autocut:
            useful_items_info = get_number_of_useful_items(
                scores,
                search_settings.autocut_min_results,
                search_settings.autocut_strategy,
                search_settings.autocut_min_score,
                search_settings.autocut_max_relative_decline,
            )
            cutoff_index = useful_items_info["count"]
            reason = useful_items_info["reason"]
            if cutoff_index != len(sorted_items):
                # TODO: there might be a better way to remove the cut items from the dictionary
                # result_set.clear()
                # for item in sorted_items[:cutoff_index]:
                #     result_set[item['_id']] = item
                positive_examples = [
                    sorted_items[max(0, cutoff_index - 5)]["_id"],
                    sorted_items[max(0, cutoff_index - 2)]["_id"],
                ]
                negative_examples = [
                    sorted_items[min(len(sorted_items) - 1, cutoff_index + 5)]["_id"],
                    sorted_items[min(len(sorted_items) - 1, cutoff_index + 2)]["_id"],
                ]
        score_info[title] = {
            "scores": normalized_scores,
            "cutoff_index": cutoff_index,
            "reason": reason,
            "max_score": max(scores),
            "min_score": min(scores),
            "positive_examples": positive_examples,
            "negative_examples": negative_examples,
        }

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
            if item["_id"] not in total_items:
                total_items[item["_id"]] = item
            else:
                total_items[item["_id"]]["_origins"] += item["_origins"]
                if "_relevant_parts" in item:
                    if "_relevant_parts" not in total_items[item["_id"]]:
                        total_items[item["_id"]]["_relevant_parts"] = []
                    total_items[item["_id"]]["_relevant_parts"] += item["_relevant_parts"]

    for item in total_items.values():
        item["_reciprocal_rank_score"] = sum([1.0 / origin["rank"] for origin in item["_origins"]])

    if len(result_sets) > 1:
        for item in total_items.values():
            item["_score"] = math.sqrt(item["_reciprocal_rank_score"])  # making the score scale linear again
    else:
        for item in total_items.values():
            item["_score"] = item["_origins"][0]["score"]
    timings.log("rank fusion")
    return total_items


def sort_items_and_complete_them(
    dataset: DotDict, total_items: dict, required_fields: list[str], limit: int, timings: Timings
) -> tuple[list[str], dict[str, dict]]:
    # TODO: check how much faster it is to get partial results from search engines and only fill in missing fields
    sorted_ids = sorted(total_items.keys(), key=lambda id: total_items[id]["_reciprocal_rank_score"], reverse=True)
    for id_to_remove in sorted_ids[limit:]:
        del total_items[id_to_remove]
    sorted_ids = sorted_ids[:limit]
    # adding reciprocal rank scores to the items to be able to compare it in the UI with reranked results:
    for rank, item_id in enumerate(sorted_ids):
        item = total_items[item_id]
        if "_origins" not in item:
            item["_origins"] = []
        item["_origins"].append(
            {
                "type": "reciprocal_rank_score",
                "field": None,
                "query": None,
                "score": item["_reciprocal_rank_score"],
                "rank": rank + 1,
            }
        )
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
    rendering = dataset.schema.result_list_rendering if purpose == "list" else dataset.schema.hover_label_rendering
    required_fields = rendering["required_fields"]

    if (
        purpose == "map"
        and vectorize_settings.map_vector_field
        and vectorize_settings.map_vector_field not in required_fields
    ):
        required_fields.append(vectorize_settings.map_vector_field)

    if purpose == "map" and dataset.schema.thumbnail_image:
        required_fields.append(dataset.schema.thumbnail_image)

    if purpose == "map":
        # used for cluster titles:
        # TODO: this may be slow, maybe use only subset for cluster titles?
        required_fields += dataset.schema.descriptive_text_fields
        required_fields += dataset.schema.get("statistics", {}).get("required_fields", [])

    if dataset.schema.is_group_field:
        required_fields.append(dataset.schema.is_group_field)

    required_fields = list(set(required_fields))
    return required_fields


def separate_text_and_vector_fields(dataset: DotDict, fields: Iterable[str]):
    vector_fields = []
    text_fields = []
    for field in fields:
        if dataset.schema.object_fields[field].field_type == FieldType.VECTOR:
            vector_fields.append(field)
        else:
            text_fields.append(field)
    return text_fields, vector_fields


def get_fulltext_search_results(
    dataset: DotDict,
    text_fields: list[str],
    query: QueryInput,
    filters: list[dict],
    required_fields: list[str],
    limit: int,
    page: int,
    return_highlights: bool = False,
    use_bolding_in_highlights: bool = True,
    auto_relax_query: bool = False,
    ranking_settings: DotDict | None = None,
) -> tuple[dict[str, dict], int]:
    boost_function = ranking_settings.get("boost_function") if ranking_settings else None
    sort_settings = ranking_settings.get("sort") if ranking_settings else None

    if not query.positive_query_str and not sort_settings:
        # if no query and just filters are used, sort results alphabetical on the title (first descr. text field):
        sort_field = dataset.schema.advanced_options.get("default_sort_field")
        if sort_field:
            sort_settings = [{sort_field: {"missing": "_last", "order": "asc"}}]
            if dataset.schema.is_group_field:
                sort_settings = [
                    {dataset.schema.is_group_field: {"missing": "_last", "order": "desc"}},
                    *sort_settings,
                ]

    text_db_client = TextSearchEngineClient.get_instance()
    search_result, total_matches = text_db_client.get_search_results(
        dataset,
        text_fields,
        filters,
        query.positive_query_str,
        "",
        page,
        limit,
        required_fields,
        highlights=return_highlights,
        use_bolding_in_highlights=use_bolding_in_highlights,
        sort_settings=sort_settings,
        boost_function=boost_function,
    )
    if auto_relax_query and total_matches == 0:
        search_result, total_matches = text_db_client.get_search_results(
            dataset,
            text_fields,
            filters,
            query.positive_query_str,
            "",
            page,
            limit,
            required_fields,
            highlights=return_highlights,
            use_bolding_in_highlights=use_bolding_in_highlights,
            default_operator="or",
            sort_settings=sort_settings,
            boost_function=boost_function,
        )
    items = {}
    # TODO: required_fields is not implemented properly, the actual item data would be in item["_source"] and needs to be copied
    ignored_keyword_highlight_fields = dataset.merged_advanced_options.ignored_keyword_highlight_fields or []
    for i, item in enumerate(search_result):
        relevant_parts = []
        for field_name, highlights in item.get("highlight", {}).items():
            if field_name in ignored_keyword_highlight_fields:
                continue
            for highlight in highlights:
                relevant_parts.append(
                    {"origin": "keyword_search", "field": field_name, "index": None, "value": highlight}
                )

        items[item["_id"]] = {
            "_id": item["_id"],
            "_dataset_id": dataset.id,
            "_origins": [
                {
                    "type": "keyword",
                    "field": None,
                    "query": query.positive_query_str,
                    "score": item["_score"],
                    "rank": i + 1,
                }
            ],
            "_relevant_parts": relevant_parts,
        }
    return items, total_matches


def get_suitable_generator(dataset, vector_field: str, mode: Literal["ingest", "search"] = "ingest"):
    generators = Generator.objects.all()
    field = dataset.schema.object_fields[vector_field]
    embedding_space_identifier = (
        field.generator.embedding_space.identifier if field.generator else field.embedding_space.identifier
    )

    # for text query:
    suitable_generator = None
    for generator in generators:
        if (
            generator.embedding_space
            and generator.embedding_space.identifier == embedding_space_identifier
            and generator.input_type == FieldType.TEXT
        ):
            suitable_generator = generator

    if not suitable_generator:
        return None

    if (
        field.generator
        and field.generator.input_type == FieldType.TEXT
        and not (suitable_generator and suitable_generator.is_preferred_for_search)
    ):
        generator_function = get_generator_function_from_field(
            dataset.schema.object_fields[vector_field], always_return_single_value_per_item=True, mode=mode
        )
    else:
        generator_function = get_generator_function(
            suitable_generator.module, suitable_generator.default_parameters or {}, False, mode=mode
        )
    return generator_function


def get_vector_search_results(
    dataset: DotDict,
    vector_field: str,
    query: QueryInput,
    query_vector: list | None,
    filters: list[dict] | None,
    required_fields: list[str],
    internal_input_weight: float,
    limit: int,
    page: int,
    score_threshold: float | None,
    max_sub_items: int | None = 1,
) -> dict[str, dict]:
    positive_query_vector = None
    negative_query_vector = None
    if query.positive_query_str or query.negative_query_str:
        generator_function = get_suitable_generator(dataset, vector_field, mode="search")
        if not generator_function:
            return {}
        if query.positive_query_str:
            positive_query_vector = generator_function([[query.positive_query_str]])[0]
        if query.negative_query_str:
            negative_query_vector = generator_function([[query.negative_query_str]])[0]

        # for image query:
        # TODO: same thing again, average both vectors

    if query_vector is None and positive_query_vector is None:
        # search using only negative query or only filters isn't supported at the moment
        return {}
    if query_vector is None:
        query_vector = positive_query_vector
    elif positive_query_vector is not None:
        assert query_vector is not None
        query_vector = (
            internal_input_weight * np.array(query_vector) + (1.0 - internal_input_weight) * positive_query_vector
        )
    if negative_query_vector is not None:
        query_vector = query_vector - negative_query_vector * (1.0 - internal_input_weight)

    vector_db_client = VectorSearchEngineClient.get_instance()
    assert query_vector is not None
    is_array_field = dataset.schema.object_fields[vector_field].is_array
    array_source_field = (
        dataset.schema.object_fields[vector_field].source_fields[0]
        if is_array_field and dataset.schema.object_fields[vector_field].source_fields
        else None
    )
    vector_search_result = vector_db_client.get_items_near_vector(
        dataset,
        vector_field,
        query_vector,
        filters,
        return_vectors=False,
        limit=limit,
        page=page,
        score_threshold=score_threshold,
        is_array_field=is_array_field,
        max_sub_items=max_sub_items or 1,
    )
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            "_id": item.id,
            "_dataset_id": dataset.id,
            "_origins": [
                {
                    "type": "vector",
                    "field": vector_field,
                    "query": query.positive_query_str,
                    "score": item.score,
                    "rank": i + 1,
                }
            ],
        }
        if is_array_field:
            items[item.id]["_relevant_parts"] = [
                {"origin": "vector_array", "field": array_source_field, "index": item.array_index}
            ]

    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]

    return items


def get_vector_search_results_matching_collection(
    dataset: DotDict,
    vector_field: str,
    positive_ids,
    negative_ids,
    required_fields: list[str],
    limit: int,
    page: int,
    score_threshold: float | None,
) -> dict[str, dict]:
    vector_db_client = VectorSearchEngineClient.get_instance()
    criteria = {}  # TODO: add criteria
    vector_search_result = vector_db_client.get_items_matching_collection(
        dataset.actual_database_name,
        vector_field,
        positive_ids,
        negative_ids,
        criteria,
        return_vectors=False,
        limit=limit,
        score_threshold=score_threshold,
    )
    items = {}
    for i, item in enumerate(vector_search_result):
        items[item.id] = {
            "_id": item.id,
            "_dataset_id": dataset.id,
            "_origins": [
                {
                    "type": "vector",
                    "field": vector_field,
                    "query": "matching a collection",
                    "score": item.score,
                    "rank": i + 1,
                }
            ],
        }
    # TODO: if purpose is map, get vectors directly from vector DB:
    # result_item[map_vector_field] = vector_search_result.vector[search_vector_field]
    return items


def fill_in_details_from_text_storage(dataset: DotDict, items: dict[str, dict], required_fields: list[str]):
    if not items:
        return
    if (
        dataset.source_plugin != SourcePlugin.INTERNAL_OPENSEARCH_QDRANT
        and dataset.source_plugin != SourcePlugin.REMOTE_DATASET
    ):
        return
    if all(all(field in item for field in required_fields) for item in items.values()):
        # all required fields are already present
        return
    ids = list(items.keys())
    search_engine_client = TextSearchEngineClient.get_instance()
    full_items = search_engine_client.get_items_by_ids(dataset, ids, fields=required_fields)
    for full_item in full_items:
        items[full_item["_id"]].update(full_item)


def fill_in_vector_data_list(dataset: DotDict, items: list[dict], required_vector_fields: list[str]):
    items_by_id = {item["_id"]: item for item in items}
    fill_in_vector_data(dataset, items_by_id, required_vector_fields)


def fill_in_vector_data(dataset: DotDict, items: dict[str, dict], required_vector_fields: list[str]):
    if not items or not required_vector_fields:
        return
    if (
        dataset.source_plugin != SourcePlugin.INTERNAL_OPENSEARCH_QDRANT
        and dataset.source_plugin != SourcePlugin.REMOTE_DATASET
    ):
        return
    if all(all(field in item for field in required_vector_fields) for item in items.values()):
        # all required fields are already present
        return
    ids = list(items.keys())
    vector_db_client = VectorSearchEngineClient.get_instance()
    for vector_field in required_vector_fields:
        is_array_field = dataset.schema.object_fields[vector_field].is_array
        results = vector_db_client.get_items_by_ids(
            dataset, ids, vector_field, is_array_field, return_vectors=True, return_payloads=False
        )
        for result in results:
            items[result.id][vector_field] = result.vector[vector_field]


def get_field_similarity_threshold(field: DotDict, input_is_image: bool | None = None):
    if input_is_image is None:
        # if not determined by other means, use same type as this field:
        input_is_image = field.generator.input_type == FieldType.IMAGE if field.generator else False
    score_threshold = field.image_similarity_threshold if input_is_image else field.text_similarity_threshold
    if score_threshold is None and field.generator:
        score_threshold = (
            field.generator.image_similarity_threshold if input_is_image else field.generator.text_similarity_threshold
        )
    return score_threshold


def get_relevant_parts_of_item_using_query_vector(
    dataset: DotDict,
    item_id: str,
    vector_field: str,
    query_vector: list,
    score_threshold: float | None = None,
    limit: int = 5,
    min_results: int = 2,
    rerank: bool = False,
    query: str | None = None,
    source_texts: list[str] | None = None,
    oversample_for_reranking: int = 3,
) -> dict:
    vector_db_client = VectorSearchEngineClient.get_instance()
    num_results = limit + oversample_for_reranking if rerank else limit
    if source_texts and len(source_texts) == 1:
        vector_search_results = [DotDict({"score": 1.0, "payload": {"array_index": 0}})]
    else:
        vector_search_results = vector_db_client.get_best_sub_items(
            dataset.actual_database_name,
            vector_field,
            item_id,
            query_vector,
            score_threshold,
            num_results,
            min_results,
        )
    if rerank and query and source_texts and len(vector_search_results) > 1:
        texts = [source_texts[item.payload["array_index"]] for item in vector_search_results]
        reranking = get_reranking_results(query, tuple(texts), limit)
        vector_search_results = [vector_search_results[rerank_result.index] for rerank_result in reranking.results]
    if len(vector_search_results) == 0:
        logging.warning(
            f"No relevant parts found for item {item_id} using vector search, this should not happen if the item is expected to have full text chunks"
        )
    score = max(*(item.score for item in vector_search_results), 0.0) if len(vector_search_results) > 0 else 0.0
    item = {
        "_id": item_id,
        "_dataset_id": dataset.id,
        "_origins": [{"type": "vector", "field": vector_field, "query": "unknown", "score": score, "rank": 1}],
    }
    array_source_field = (
        dataset.schema.object_fields[vector_field].source_fields[0]
        if dataset.schema.object_fields[vector_field].source_fields
        else None
    )
    item["_relevant_parts"] = [
        {
            "origin": "vector_array",
            "field": array_source_field,
            "index": item.payload["array_index"],
            "score": item.score,
        }
        for item in vector_search_results
    ]
    return item


def _field_is_available_for_filtering(field: DotDict, retrieval_mode: str):
    if not field.is_available_for_filtering:
        return False
    index_params = field.index_parameters or DotDict({})
    no_index_in_vector_db = index_params.no_index_in_vector_database or index_params.exclude_from_vector_database
    return not (retrieval_mode != "keyword" and no_index_in_vector_db)


def check_filters(dataset: DotDict, filters: list[dict], retrieval_mode: str):
    for filter_ in filters:
        if filter_["field"] == "_descriptive_text_fields":
            continue
        if filter_["field"] == "_parent":
            continue
        if filter_["field"] == "_all_parents":
            continue
        if filter_["field"] == "_id":
            continue
        if filter_["field"] not in dataset.schema.object_fields:
            raise ValueError(f"Filter field '{filter_['field']}' not found")
        field = DotDict(dataset.schema.object_fields[filter_["field"]])
        if not field.is_available_for_filtering:
            raise ValueError(f"Field '{field.name}' is not available for filtering")
        if not _field_is_available_for_filtering(field, retrieval_mode):
            raise ValueError(f"Field '{field.name}' is not available for filtering in 'meaning' or 'hybrid' mode")


def adapt_filters_to_dataset(
    filters: list[dict], dataset: DotDict, limit: int, retrieval_mode: str, result_language: str | None = None
):
    filters = copy.deepcopy(filters)
    additional_filters = []
    removed_filters = []
    for filter_ in filters:
        if filter_["field"] == "_descriptive_text_fields":
            descriptive_text_fields = [
                f
                for f in dataset.schema.descriptive_text_fields
                if _field_is_available_for_filtering(DotDict(dataset.schema.object_fields[f]), retrieval_mode)
            ]
            if filter_["operator"] == "contains":
                # only in this case a list of fields is allowed, as it needs to be concatenated as OR filters (aka 'should')
                filter_["field"] = descriptive_text_fields
            else:
                for field in descriptive_text_fields:
                    additional_filters.append(
                        {"field": field, "value": filter_["value"], "operator": filter_["operator"]}
                    )
                removed_filters.append(filter_)
    # FIXME: disable hard language filtering for now, as it is often not wanted, rather use manual filters for now
    # if result_language and dataset.merged_advanced_options.get("language_filtering"):
    #     language_filtering = dataset.merged_advanced_options.language_filtering
    #     if not language_filtering.format == "iso_639_set_1":
    #         logging.warning(f"Unsupported language filtering format '{language_filtering.format}'")
    #     else:
    #         additional_filters.append({"field": language_filtering.field, "value": result_language, "operator": "is"})
    filters.extend(additional_filters)
    for filter_ in filters:
        if filter_ in removed_filters:
            continue
        if not isinstance(filter_["field"], list) and filter_["field"] in dataset.schema.object_fields:
            field = dataset.schema.object_fields[filter_["field"]]
            if field.field_type == FieldType.INTEGER:
                try:
                    filter_["value"] = int(filter_["value"])
                except ValueError:
                    logging.warning(
                        f"Could not convert filter value '{filter_['value']}' to integer for field '{field.name}'"
                    )
                    removed_filters.append(filter_)
            elif field.field_type == FieldType.FLOAT:
                try:
                    filter_["value"] = float(filter_["value"])
                except ValueError:
                    logging.warning(
                        f"Could not convert filter value '{filter_['value']}' to float for field '{field.name}'"
                    )
                    removed_filters.append(filter_)
            elif field.field_type == FieldType.STRING and filter_["operator"] in ["is", "is_not"]:
                filter_["field"] = filter_["field"] + ".keyword"
    for filter_ in removed_filters:
        filters.remove(filter_)
    workaround_to_filter_by_institution_using_openalex(dataset, filters, limit)
    return filters


def workaround_to_filter_by_institution_using_openalex(dataset, filters, limit):
    if dataset.schema.identifier not in ["semantic_scholar", "openalex"]:
        return None

    for filter_ in filters.copy():
        if filter_["field"] == "institution":
            institution_query = filter_["value"]
            institution_info = openalex_api.search_institution(institution_query)["results"][0]
            institution_id = institution_info["id"]
            filters.remove(filter_)
            if dataset.schema.identifier == "openalex":
                import uuid

                # workaround for DOI not being stored as 'keyword' (and therefore not searchable) in our OpenAlex database:
                openalex_ids = openalex_api.get_ids_of_institution(institution_id, max_results=min(limit, 65000))
                # OpenAlex ids are urls like "https://openalex.org/works/W123124", only the last part was used during ingest:
                openalex_ids = [oid.split("/")[-1] for oid in openalex_ids]
                # mimicking the way the ids were generated during ingest:
                ids = [pk_to_uuid_id(oid) for oid in openalex_ids]
                filters.append({"field": "_id", "value": ids, "operator": "in"})
            else:
                # OpenSearch allows a max of 65k elements by default, no limit on OpenAlex API side for now
                ids = openalex_api.get_dois_of_institution(institution_id, max_results=min(limit, 65000))
                filters.append({"field": "doi", "value": ids, "operator": "in"})
            return institution_info["display_name"]

    return None


# --- Workaround for getting OpenAccess PDF links from disk for semantic_scholar dataset ---
# should be replaced soon by storing this link in OpenSearch index

import pickle
import time
from pathlib import Path

import orjson

base_download_folder = f"/data/semantic_scholar"
abstract_files = {}
abstract_file_paths = {}
corpus_ids = None
file_ids = None
file_positions = None


def load_indexes():
    global corpus_ids, file_ids, file_positions, abstract_file_paths
    abstract_file_paths, corpus_ids, file_ids, file_positions = pickle.load(
        open(Path(base_download_folder) / f"abstracts.flat_index.pkl", "rb")
    )
    # takes about 1s and 2GB memory


def get_abstract(corpusid):
    if corpus_ids is None:
        load_indexes()
    # t1 = time.time()
    assert corpus_ids is not None
    assert file_ids is not None
    assert file_positions is not None
    # corpus_ids is a sorted numpy array of integers
    index = np.searchsorted(corpus_ids, corpusid)
    if index >= len(corpus_ids) or corpus_ids[index] != corpusid:
        return {}
    file_id = file_ids[index]
    pos = file_positions[index]
    file_path = abstract_file_paths[file_id]
    if file_path not in abstract_files:
        # logging.warning(f"Opening file {file_path}")
        abstract_files[file_path] = open(file_path, "rb")
    file = abstract_files[file_path]
    file.seek(pos)
    line = file.readline()
    data = orjson.loads(line)
    # duration_ms = (time.time() - t1) * 1000
    # logging.warning(f"get_abstract took {duration_ms:.2f} ms")  # about 0.16ms on average
    return data


# --- End of Workaround for getting OpenAccess PDF links from disk for semantic_scholar dataset ---


@cachetools.func.ttl_cache(maxsize=128, ttl=1)  # seconds
def get_document_details_by_id(
    dataset_id: int,
    item_id: str,
    fields: tuple[str, ...],
    relevant_parts: str | None = None,
    database_name: str | None = None,
    top_n_full_text_chunks: int | None = None,
    get_text_search_highlights: bool = False,
    query: str | None = None,
    include_related_collection_items: bool = False,
) -> dict | None:
    dataset = get_serialized_dataset_cached(dataset_id)
    if not database_name:
        database_name = dataset.actual_database_name
        assert database_name is not None
    additional_fields = []
    if dataset.schema.identifier == "semantic_scholar":
        # for workaround to add data from disk for semantic_scholar dataset:
        additional_fields.append("corpus_id")
    relevant_parts_list = []
    original_fields = fields
    if relevant_parts:
        relevant_parts_list = json.loads(relevant_parts)
        assert isinstance(relevant_parts_list, list)
        for relevant_part in relevant_parts_list:
            assert isinstance(relevant_part, dict)
            if relevant_part.get("origin") == "vector_array" and not relevant_part.get("value"):
                # this is a relevant chunk that needs to be materialized (only the index is known):
                # logging.warning(f"Materializing chunk for field {relevant_part.get('field')} and index {relevant_part.get('index')}")
                additional_fields.append(relevant_part.get("field"))

    get_new_full_text_chunks = False
    if top_n_full_text_chunks and query:
        chunk_vector_field_name = dataset.merged_advanced_options.get("full_text_chunk_embeddings")
        if chunk_vector_field_name:
            chunk_vector_field = DotDict(dataset.schema.object_fields.get(chunk_vector_field_name))
            chunk_field = chunk_vector_field.source_fields[0]
            additional_fields.append(chunk_field)
            get_new_full_text_chunks = True

    search_engine_client = TextSearchEngineClient.get_instance()
    all_fields = list(set(list(fields) + additional_fields))
    items = search_engine_client.get_items_by_ids(dataset, [item_id], fields=all_fields)
    if not items:
        return None
    item = items[0]
    item["_dataset_id"] = dataset_id

    # workaround to add data from disk for semantic_scholar dataset:
    if dataset.schema.identifier == "semantic_scholar":
        try:
            abstract = get_abstract(int(item["corpus_id"]))
        except Exception as e:
            logging.warning(f"Could not get abstract for corpus_id {item.get('corpus_id')}: {e}")
            abstract = {}
        item["oa_url"] = (abstract.get("openaccessinfo") or {}).get("url")
        item["oa_status"] = (abstract.get("openaccessinfo") or {}).get("status")
        item["oa_license"] = (abstract.get("openaccessinfo") or {}).get("license")

    if get_text_search_highlights:
        filters = [{"field": "_id", "value": [item_id], "operator": "in"}]
        ignored_keyword_highlight_fields = dataset.merged_advanced_options.ignored_keyword_highlight_fields or []
        results, total = search_engine_client.get_search_results(
            dataset,
            dataset.schema.default_search_fields,
            filters,
            "",
            "",
            0,
            1,
            ["_id"],
            highlights=True,
            use_bolding_in_highlights=True,
            highlight_query=query,
            ignored_highlight_fields=ignored_keyword_highlight_fields,
        )
        relevant_parts_list.extend(
            [
                {"origin": "keyword_search", "field": field_name, "index": None, "value": " [...] ".join(highlights)}
                for field_name, highlights in results[0].get("highlight", {}).items()
                if field_name not in ignored_keyword_highlight_fields
            ]
        )

    if get_new_full_text_chunks:
        generator_function = get_suitable_generator(dataset, chunk_vector_field_name, mode="search")
        assert generator_function is not None and isinstance(top_n_full_text_chunks, int)
        query_vector = generator_function([[query]])[0]
        score_threshold = get_field_similarity_threshold(chunk_vector_field, input_is_image=False)
        chunks = item.get(chunk_field, [])
        new_relevant_parts = get_relevant_parts_of_item_using_query_vector(
            dataset,
            item_id,
            chunk_vector_field_name,
            query_vector,
            score_threshold,
            top_n_full_text_chunks,
            rerank=True,
            query=query,
            source_texts=chunks,
        ).get("_relevant_parts", [])
        for i in range(len(relevant_parts_list) - 1, -1, -1):
            if relevant_parts_list[i].get("field") == chunk_field:
                del relevant_parts_list[i]
        relevant_parts_list.extend(new_relevant_parts)

    if relevant_parts_list:
        for relevant_part in relevant_parts_list:
            if relevant_part["index"] is not None:
                # materialize chunk text:
                try:
                    relevant_part["value"] = item[relevant_part["field"]][relevant_part["index"]]
                except (IndexError, KeyError):
                    relevant_part["value"] = None
                relevant_part["array_size"] = len(item.get(relevant_part["field"], []))
        item["_relevant_parts"] = relevant_parts_list

    for field in additional_fields:
        if field not in original_fields and field in item:
            del item[field]

    if include_related_collection_items:
        item["_related_collection_items"] = get_related_collection_items(dataset_id, item_id, include_column_data=True)

    return item
