import json
import logging
import threading
from typing import Callable

import dspy
from django.utils import timezone

from columns.logic.process_column import process_cells_blocking
from config.utils import get_default_dspy_llm
from data_map_backend.models import (
    CollectionColumn,
    CollectionItem,
    DataCollection,
    Dataset,
    FieldType,
    SearchTask,
    User,
)
from data_map_backend.views.other_views import get_dataset_cached
from legacy_backend.logic.search import get_search_results
from search.logic.approve_items_and_exit_search import (
    approve_using_comparison,
    auto_approve_items,
    exit_search_mode,
)
from search.schemas import (
    RetrievalMode,
    RetrievalParameters,
    RetrievalStatus,
    SearchTaskSettings,
    SearchType,
)

# from search.logic.extract_filters import get_filter_prompt, extract_filters


class SearchQuerySignature(dspy.Signature):
    """
    Write a search query that you would use to find the following information.
     If the user input is already a search query, write the same query.

     Examples:
     User input: "What is the capital of France?"
     Search query: "capital of France"

     User input: "a technical drawing of a car in a PDF file"
     Search query: "technical drawing car PDF"
    """

    user_input: str = dspy.InputField()
    target_language: str = dspy.InputField()
    search_query: str = dspy.OutputField(desc="Resulting search query in target_languge")


search_query_predictor = dspy.Predict(SearchQuerySignature)


def create_and_run_search_task(
    collection: DataCollection,
    search_task: SearchTaskSettings,
    user: User,
    after_columns_were_processed: Callable | None = None,
    is_new_collection: bool = False,
    return_task_object: bool = False,
    set_agent_step: bool = True,
) -> list[CollectionItem] | tuple[list[CollectionItem], SearchTask]:
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
    if set_agent_step:
        collection.current_agent_step = "Running search task..."
        collection.save(update_fields=["current_agent_step"])

    keyword_query = search_task.user_input

    # TODO: use dataset cache as this increases latency of every search
    dataset = Dataset.objects.select_related("schema").get(id=search_task.dataset_id)

    if search_task.auto_set_filters:

        if search_task.user_input:
            collection.log_explanation("Use AI model to generate **suitable query**", save=False)
            model = get_default_dspy_llm("search_query")
            try:
                with dspy.context(lm=dspy.LM(**model.to_litellm())):
                    keyword_query = (
                        search_query_predictor(
                            user_input=search_task.user_input, target_language=search_task.result_language or "en"
                        ).search_query
                        or keyword_query
                    )
            except Exception as e:
                logging.error(f"Error generating search query: {e}")

            # filter_prompt_template = get_filter_prompt(search_task.dataset_id, search_task.result_language or 'en')
            # if filter_prompt_template:
            #     collection.log_explanation("Use AI model to determine **best filters settings**", save=False)
            #     filter_prompt = filter_prompt_template.replace("{{ user_input }}", search_task.user_input)
            #     filters = extract_filters(search_task, filter_prompt)
            #     if filters:
            #         search_task.filters = filters

        # TODO: also get best ranking mode?

        ranking_options = dataset.merged_advanced_options.get("ranking_options", [])
        if not search_task.ranking_settings:
            search_task.ranking_settings = ranking_options[0] if ranking_options else {}

        # if no user input was provided (e.g. to show all items), make sure to use an appropriate ranking mode:
        if search_task.ranking_settings.get("needs_user_input") and not search_task.user_input:
            # get first option that doesn't need user input (e.g. alphabetical or newest first instead of relevance):
            for option in ranking_options:
                if not option.get("needs_user_input"):
                    search_task.ranking_settings = option
                    break

    default_filters: list = dataset.merged_advanced_options.get("default_filters", [])
    if default_filters:
        search_task.filters = search_task.filters or []
        for filter in default_filters:
            if any(f["field"] == filter["field"] for f in search_task.filters):
                continue
            filter["dataset_id"] = search_task.dataset_id
            search_task.filters.append(filter)

    parameters = RetrievalParameters(
        created_at=timezone.now().isoformat(),
        search_type=search_task.search_type,
        dataset_id=search_task.dataset_id,
        result_language=search_task.result_language or "en",
        limit=search_task.candidates_per_step,  # uses max_candidates if not from_ui
        # external_input
        keyword_query=keyword_query,
        vector=None,
        filters=search_task.filters or [],
        ranking_settings=search_task.ranking_settings or {},
        retrieval_mode=search_task.retrieval_mode or "hybrid",
        auto_relax_query=search_task.auto_relax_query,
        use_reranking=search_task.use_reranking,
        # similar_to_item
        reference_item_id=search_task.reference_item_id,
        reference_dataset_id=search_task.reference_dataset_id,
        origin_name=search_task.origin_name,
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
    items = run_search_task(
        task,
        user,
        after_columns_were_processed=after_columns_were_processed,
        is_new_collection=is_new_collection,
        set_agent_step=False,
        from_ui=True,
    )
    if return_task_object:
        return items, task
    return items


def run_search_task(
    task: SearchTask,
    user: User,
    after_columns_were_processed: Callable | None = None,
    is_new_collection: bool = False,
    set_agent_step: bool = True,
    from_ui: bool = False,
    restrict_to_item_ids: list[str] | None = None,
) -> list[CollectionItem]:
    collection = task.collection
    if set_agent_step and from_ui:
        collection.current_agent_step = "Running search task..."
        collection.save(update_fields=["current_agent_step"])

    exit_search_mode(collection, "_default", from_ui)  # removes candidates
    search_task = SearchTaskSettings(**task.settings)

    if from_ui:
        collection.most_recent_search_task = task  # type: ignore
        if not search_task.exit_search_mode:
            collection.search_task_navigation_history.append(str(task.id))

        collection.save(update_fields=["most_recent_search_task", "search_task_navigation_history"])

    def after_columns_were_processed_internal(new_items):
        if search_task.auto_approve:
            auto_approve_items(
                collection, new_items, search_task.max_selections, search_task.forced_selections, from_ui
            )
        elif search_task.approve_using_comparison:
            if from_ui:
                collection.log_explanation(
                    "Use AI model to **compare search results** and **approve best items**", save=False
                )
            approve_using_comparison(
                collection, new_items, search_task, search_task.max_selections, search_task.forced_selections
            )
        elif not from_ui and task.run_on_new_items:
            auto_approve_items(
                collection, new_items, search_task.max_selections, search_task.forced_selections, from_ui
            )

        if search_task.exit_search_mode or not from_ui:
            deleted_item_ids = exit_search_mode(collection, "_default", from_ui)
            new_items = [item for item in new_items if item.id not in deleted_item_ids]

        if after_columns_were_processed:
            after_columns_were_processed(new_items)

    new_items = add_items_from_task_and_run_columns(
        task, user, True, is_new_collection, from_ui, restrict_to_item_ids, after_columns_were_processed_internal
    )
    return new_items


def add_items_from_task_and_run_columns(
    task: SearchTask,
    user: User,
    ignore_last_retrieval: bool = True,
    is_new_collection: bool = False,
    from_ui: bool = True,
    restrict_to_item_ids: list[str] | None = None,
    after_columns_were_processed: Callable | None = None,
) -> list[CollectionItem]:
    collection = task.collection

    # removing visibility filters because otherwise new items might not be visible
    if from_ui and collection.filters:
        collection.filters = []
        collection.save(update_fields=["filters"])

    new_items = add_items_from_task(
        collection, task, user, ignore_last_retrieval, is_new_collection, from_ui, restrict_to_item_ids
    )

    def in_thread():
        if from_ui:
            max_processed_items = 10
            items_to_process = new_items[:max_processed_items]
        else:
            items_to_process = new_items
        for column in collection.columns.filter(auto_run_for_candidates=True):
            assert isinstance(column, CollectionColumn)
            process_cells_blocking(items_to_process, column, collection, user.id)  # type: ignore
        if after_columns_were_processed:
            after_columns_were_processed(new_items)

    threading.Thread(target=in_thread).start()

    return new_items


def add_items_from_task(
    collection: DataCollection,
    task: SearchTask,
    user: User,
    ignore_last_retrieval: bool = True,
    is_new_collection: bool = False,
    from_ui: bool = True,
    restrict_to_item_ids: list[str] | None = None,
) -> list[CollectionItem]:
    parameters = RetrievalParameters(**task.retrieval_parameters)
    status = RetrievalStatus(**task.last_retrieval_status)

    if not get_dataset_cached(parameters.dataset_id).user_has_permission(user):
        logging.warning(
            f"User {user.id}: {user.email} doesn't have permission to access dataset {parameters.dataset_id}"
        )
        return []

    if not from_ui:
        # directly retrieve all items
        parameters.limit = task.settings.get("max_candidates", 10)

    if parameters.retrieval_mode != RetrievalMode.KEYWORD and restrict_to_item_ids:
        logging.warning("Restricting to item IDs is only supported for keyword search for now")
        # because for vector search without having a threshold, it would just add all items
        return []

    legacy_params = _convert_retrieval_parameters_to_old_format(
        parameters, status, ignore_last_retrieval, restrict_to_item_ids
    )
    results = get_search_results(json.dumps(legacy_params), "list")

    new_items = []
    updated_items = []
    if results["sorted_ids"]:
        items_by_dataset = results["items_by_dataset"]
        existing_items_by_id = {}
        if not is_new_collection:
            existing_items = CollectionItem.objects.filter(
                collection=collection,
                dataset_id=parameters.dataset_id,
                item_id__in=[ds_and_item_id[1] for ds_and_item_id in results["sorted_ids"]],
            )
            existing_items_by_id = {item.item_id: item for item in existing_items}
        for i, ds_and_item_id in enumerate(results["sorted_ids"]):
            value = items_by_dataset[ds_and_item_id[0]][ds_and_item_id[1]]
            if ds_and_item_id[1] in existing_items_by_id:
                item = existing_items_by_id[ds_and_item_id[1]]
                item.search_source_id = str(task.id)
                item.search_score = 1 / (status.retrieved + i + 1)
                item.relevant_parts = value.get("_relevant_parts", [])
                updated_items.append(item)
                continue
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
                # TODO: mark this item as added in background if from_ui is False?
            )
            new_items.append(item)
        CollectionItem.objects.bulk_create(new_items)
        CollectionItem.objects.bulk_update(updated_items, ["search_source_id", "search_score", "relevant_parts"])
        collection.items_last_changed = timezone.now()

    collection.search_mode = True
    if from_ui:
        if ignore_last_retrieval:
            status.retrieved = len(results["sorted_ids"])
        else:
            status.retrieved += len(results["sorted_ids"])
        status.available = max(results["total_matches"], status.retrieved)
        status.available_is_exact = (
            parameters.retrieval_mode == RetrievalMode.KEYWORD or len(results["sorted_ids"]) < parameters.limit
        )
        task.last_retrieval_status = status.dict()
        task.save(update_fields=["last_retrieval_status"])

        if parameters.retrieval_mode == RetrievalMode.KEYWORD:
            collection.log_explanation(
                f"Added {len(new_items)} search results found by **included keywords**", save=False
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

        collection.save(update_fields=["search_mode", "items_last_changed", "explanation_log"])
    else:
        collection.save(update_fields=["search_mode", "items_last_changed"])
    return new_items + updated_items


def _convert_retrieval_parameters_to_old_format(
    retrieval_parameters: RetrievalParameters,
    status: RetrievalStatus,
    ignore_last_retrieval: bool = True,
    restrict_to_item_ids: list[str] | None = None,
) -> dict:
    filters = retrieval_parameters.filters or []
    if restrict_to_item_ids is not None:
        filters.append(
            {
                "field": "_id",
                "dataset_id": retrieval_parameters.dataset_id,  # not sure if this is needed
                "operator": "in",
                "value": restrict_to_item_ids,
            }
        )
    params = {
        "search": {
            "dataset_ids": [retrieval_parameters.dataset_id],
            "task_type": "quick_search",
            "search_type": retrieval_parameters.search_type,
            "retrieval_mode": retrieval_parameters.retrieval_mode or "hybrid",
            "use_separate_queries": False,
            "all_field_query": retrieval_parameters.keyword_query,
            "internal_input_weight": 0.7,
            "use_similarity_thresholds": True,
            # auto relax query doesn't make sense for periodic tasks, where restrict_to_item_ids is usually used
            "auto_relax_query": not restrict_to_item_ids and retrieval_parameters.auto_relax_query,
            "use_reranking": (
                # restrict_to_item_ids is usually used when adding items in the background, reranking isn't needed then
                not restrict_to_item_ids and retrieval_parameters.use_reranking
                if retrieval_parameters.search_type == SearchType.EXTERNAL_INPUT
                else False
            ),
            "filters": filters,
            "result_language": retrieval_parameters.result_language or "en",
            "ranking_settings": retrieval_parameters.ranking_settings or {},
            "similar_to_item_id": (
                [retrieval_parameters.reference_dataset_id, retrieval_parameters.reference_item_id]
                if retrieval_parameters.reference_item_id
                else None
            ),
            "result_list_items_per_page": retrieval_parameters.limit,
            "result_list_current_page": (
                status.retrieved // retrieval_parameters.limit if status.retrieved and not ignore_last_retrieval else 0
            ),
            "max_sub_items_per_item": 1,
            "return_highlights": True,
            "use_bolding_in_highlights": True,
            # TODO: add support for vector search, similar to collection
        }
    }
    return params
