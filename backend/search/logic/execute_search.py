import json
import logging
import threading
from typing import Callable

from django.utils import timezone
from llmonkey.llms import Google_Gemini_Flash_1_5_v1

from columns.logic.process_column import process_cells_blocking
from data_map_backend.models import (
    CollectionColumn,
    CollectionItem,
    DataCollection,
    FieldType,
    SearchTask,
)
from legacy_backend.logic.search import get_search_results
from search.logic.approve_items_and_exit_search import (
    approve_using_comparison,
    auto_approve_items,
    exit_search_mode,
)
from search.prompts import search_query_prompt
from search.schemas import RetrievalMode, RetrievalParameters, SearchTaskSettings, SearchType, RetrievalStatus

# from search.logic.extract_filters import get_filter_prompt, extract_filters


def create_and_run_search_task(
    collection: DataCollection,
    search_task: SearchTaskSettings,
    user_id: int,
    after_columns_were_processed: Callable | None = None,
    is_new_collection: bool = False,
) -> list[CollectionItem]:
    """
    Executes a search task on a given data collection.

    Args:
        collection (DataCollection): The data collection to perform the search on.
        search_task (SearchTaskSettings): The settings for the search task.
        user_id (int): The ID of the user initiating the search.
        after_columns_were_processed (Callable, optional): A callback function to be called after columns are processed. Defaults to None.
        is_new_collection (bool, optional): Flag indicating if the collection is new. Defaults to False.

    Returns:
        list[CollectionItem]: A list of collection items resulting from the search task.
    """

    collection.current_agent_step = "Running search task..."
    collection.save(update_fields=["current_agent_step"])

    if not search_task.query:
        search_task.query = search_task.user_input

    if search_task.auto_set_filters:
        collection.log_explanation("Use AI model to generate **suitable query**", save=False)
        prompt = search_query_prompt[search_task.result_language or "en"].replace(
            "{{ user_input }}", search_task.user_input
        )
        search_task.query = Google_Gemini_Flash_1_5_v1().generate_short_text(prompt) or search_task.query

        # filter_prompt_template = get_filter_prompt(search_task.dataset_id, search_task.result_language or 'en')
        # if filter_prompt_template:
        #     collection.log_explanation("Use AI model to determine **best filters settings**", save=False)
        #     filter_prompt = filter_prompt_template.replace("{{ user_input }}", search_task.user_input)
        #     filters = extract_filters(search_task, filter_prompt)
        #     if filters:
        #         search_task.filters = filters

        # TODO: also get best ranking mode?

    parameters = RetrievalParameters(
        created_at=timezone.now().isoformat(),
        search_type=search_task.search_type,
        dataset_id=search_task.dataset_id,
        result_language=search_task.result_language or "en",
        page_size=search_task.candidates_per_step,
        # external_input
        query=search_task.query,
        vector=None,
        filters=search_task.filters or [],
        ranking_settings=search_task.ranking_settings or {},
        retrieval_mode=search_task.retrieval_mode or "hybrid",
        auto_relax_query=True,
        use_reranking=True,
        # similar_to_item
        reference_item_id=search_task.reference_item_id,
        reference_dataset_id=search_task.reference_dataset_id,
        origin_name=search_task.origin_name,
        # similar_to_collection
        reference_collection_id=search_task.reference_collection_id,
        # random_sample: no parameters, always same seed
    )
    status = RetrievalStatus(retrieved=0, available=None, available_is_exact=True)

    task = SearchTask.objects.create(
        collection=collection,
        dataset_id=search_task.dataset_id,
        settings=search_task.dict(),
        retrieval_parameters=parameters.dict(),
        last_retrieval_status=status.dict(),
    )
    return run_search_task(
        collection,
        task,
        user_id,
        after_columns_were_processed=after_columns_were_processed,
        is_new_collection=is_new_collection,
        set_agent_step=False,
    )


def run_search_task(
    collection: DataCollection,
    task: SearchTask,
    user_id: int,
    after_columns_were_processed: Callable | None = None,
    is_new_collection: bool = False,
    set_agent_step: bool = True,
) -> list[CollectionItem]:
    if set_agent_step:
        collection.current_agent_step = "Running search task..."
        collection.save(update_fields=["current_agent_step"])

    if not is_new_collection:
        exit_search_mode(collection, "_default")  # removes candidates and disables sources
    search_task = SearchTaskSettings(**task.settings)
    collection.most_recent_search_task = task  # type: ignore
    if not search_task.exit_search_mode:
        collection.search_task_navigation_history.append(str(task.id))
    collection.save(update_fields=["most_recent_search_task", "search_task_navigation_history"])

    def after_columns_were_processed_internal(new_items):
        if search_task.auto_approve:
            auto_approve_items(collection, new_items, search_task.max_selections)

        if search_task.approve_using_comparison:
            collection.log_explanation(
                "Use AI model to **compare search results** and **approve best items**", save=False
            )
            approve_using_comparison(collection, new_items, search_task.max_selections, search_task)

        if search_task.exit_search_mode:
            exit_search_mode(collection, "_default")

        if after_columns_were_processed:
            after_columns_were_processed(new_items)

    new_items = add_items_from_task_and_run_columns(
        collection, task, user_id, True, is_new_collection, after_columns_were_processed_internal
    )
    return new_items


def add_items_from_task_and_run_columns(
    collection: DataCollection,
    task: SearchTask,
    user_id: int,
    ignore_last_retrieval: bool = True,
    is_new_collection: bool = False,
    after_columns_were_processed: Callable | None = None,
) -> list[CollectionItem]:
    # removing visibility filters because otherwise new items might not be visible
    collection.filters = []
    collection.save(update_fields=["filters"])

    new_items = add_items_from_task(collection, task, ignore_last_retrieval, is_new_collection)

    def in_thread():
        max_evaluated_candidates = 10
        for column in collection.columns.all():  # type: ignore
            assert isinstance(column, CollectionColumn)
            if column.auto_run_for_candidates:
                process_cells_blocking(new_items[:max_evaluated_candidates], column, collection, user_id)
        if after_columns_were_processed:
            after_columns_were_processed(new_items)

    threading.Thread(target=in_thread).start()

    return new_items


def add_items_from_task(
    collection: DataCollection, task: SearchTask,
    ignore_last_retrieval: bool = True, is_new_collection: bool = False
) -> list[CollectionItem]:
    parameters = RetrievalParameters(**task.retrieval_parameters)
    status = RetrievalStatus(**task.last_retrieval_status)

    legacy_params = _convert_retrieval_settings_to_old_format(parameters, status, ignore_last_retrieval)
    results = get_search_results(json.dumps(legacy_params), "list")
    items_by_dataset = results["items_by_dataset"]
    new_items = []
    existing_item_ids = []
    if not is_new_collection:
        existing_item_ids = CollectionItem.objects.filter(
            collection=collection,
            dataset_id=parameters.dataset_id,
            item_id__in=[ds_and_item_id[1] for ds_and_item_id in results["sorted_ids"]],
        ).values_list("item_id", flat=True)
    for i, ds_and_item_id in enumerate(results["sorted_ids"]):
        if ds_and_item_id[1] in existing_item_ids:
            continue
        value = items_by_dataset[ds_and_item_id[0]][ds_and_item_id[1]]
        item = CollectionItem(
            date_added=parameters.created_at,
            search_source_id=task.id,
            collection=collection,
            relevance=0,
            classes=["_default"],
            field_type=FieldType.IDENTIFIER,
            dataset_id=ds_and_item_id[0],
            item_id=ds_and_item_id[1],
            metadata=value,
            search_score=1 / (status.retrieved + i + 1),
            relevant_parts=value.get("_relevant_parts", []),
        )
        new_items.append(item)
    CollectionItem.objects.bulk_create(new_items)

    if ignore_last_retrieval:
        status.retrieved = len(results["sorted_ids"])
    else:
        status.retrieved += len(results["sorted_ids"])
    status.available = max(results["total_matches"], status.retrieved)
    status.available_is_exact = (
        parameters.retrieval_mode == RetrievalMode.KEYWORD or len(results["sorted_ids"]) < parameters.page_size
    )
    task.last_retrieval_status = status.dict()
    task.save(update_fields=["last_retrieval_status"])

    collection.items_last_changed = timezone.now()
    if parameters.retrieval_mode == RetrievalMode.KEYWORD:
        collection.log_explanation(
            f"Added {len(new_items)} search results found by **included keywords**",
            save=False,
        )
    elif parameters.retrieval_mode == RetrievalMode.VECTOR:
        collection.log_explanation(
            f"Added {len(new_items)} search results found by **AI-based semantic similarity** (vector search)",
            save=False,
        )
    elif parameters.retrieval_mode == RetrievalMode.HYBRID:
        collection.log_explanation(
            f"Added {len(new_items)} search results found by a combination of **included keywords** and **AI-based semantic similarity** (vector search)",
            save=False,
        )
    if parameters.use_reranking:
        collection.log_explanation("Re-ordered top results using an **AI-based re-ranking model**", save=False)
    collection.search_mode = True
    collection.save(update_fields=["search_mode", "items_last_changed", "explanation_log"])
    return new_items


def _convert_retrieval_settings_to_old_format(
    retrieval_settings: RetrievalParameters,
    status: RetrievalStatus,
    ignore_last_retrieval: bool = True,
    ) -> dict:
    params = {
        "search": {
            "dataset_ids": [retrieval_settings.dataset_id],
            "task_type": "quick_search",
            "search_type": retrieval_settings.search_type,
            "retrieval_mode": retrieval_settings.retrieval_mode or "hybrid",
            "use_separate_queries": False,
            "all_field_query": retrieval_settings.query,
            "internal_input_weight": 0.7,
            "use_similarity_thresholds": True,
            "auto_relax_query": retrieval_settings.auto_relax_query,
            "use_reranking": retrieval_settings.use_reranking if retrieval_settings.search_type == SearchType.EXTERNAL_INPUT else False,
            "filters": retrieval_settings.filters or [],
            "result_language": retrieval_settings.result_language or "en",
            "ranking_settings": retrieval_settings.ranking_settings or {},
            "similar_to_item_id": (
                [retrieval_settings.reference_dataset_id, retrieval_settings.reference_item_id] if retrieval_settings.reference_item_id else None
            ),
            "result_list_items_per_page": retrieval_settings.page_size,
            "result_list_current_page": status.retrieved // retrieval_settings.page_size if status.retrieved and not ignore_last_retrieval else 0,
            "max_sub_items_per_item": 1,
            "return_highlights": True,
            "use_bolding_in_highlights": True,
            # TODO: add support for vector search, similar to collection
        }
    }
    return params
