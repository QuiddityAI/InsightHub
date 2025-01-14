from enum import StrEnum
import threading
import time
import logging

from django.utils import timezone
from llmonkey.llms import Mistral_Ministral3b

from data_map_backend.models import DataCollection, User, COLUMN_META_SOURCE_FIELDS, WritingTask, Dataset
from data_map_backend.schemas import CollectionUiSettings
from search.schemas import SearchTaskSettings, Filter
from search.logic.execute_search import run_search_task
from write.logic.writing_task import execute_writing_task_thread
from .schemas import CreateCollectionSettings
from .create_columns import create_relevance_column
from workflows.prompts import query_language_prompt
from workflows.agents import run_research_agent_in_collection


class Workflows(StrEnum):
    CLASSIC_SEARCH = 'classic_search'
    ASSISTED_SEARCH = 'assisted_search'
    FACT_FROM_SINGLE_DOCUMENT = 'fact_from_single_document'
    FACTS_FROM_MULTIPLE_DOCUMENTS = 'facts_from_multiple_documents'
    META_REPORT = 'meta_report'
    TIMELINE = 'timeline'
    OVERVIEW_MAP = 'overview_map'
    RESEARCH_AGENT = 'research_agent'
    SHOW_ALL = 'show_all'
    EMPTY_COLLECTION = 'empty_collection'


def create_collection_using_workflow(
    user: User, settings: CreateCollectionSettings
) -> DataCollection:
    collection = DataCollection()
    collection.created_by = user
    collection.name = settings.user_input or f"Collection {timezone.now().isoformat()}"
    if settings.workflow_id == Workflows.SHOW_ALL:
        collection.name = "All items"
    collection.related_organization_id = settings.related_organization_id  # type: ignore
    collection.agent_is_running = settings.workflow_id != Workflows.EMPTY_COLLECTION
    collection.current_agent_step = "Preparing..."
    collection.cancel_agent_flag = False
    collection.save()
    # above takes about 17 ms

    def thread_function():
        try:
            # creating thread takes about 0.6ms
            prepare_collection(collection, settings, user)
            # preparing collection just for classic search takes up to 100ms
        except Exception as e:
            collection.agent_is_running = False
            collection.save()
            raise e

    if settings.workflow_id != Workflows.EMPTY_COLLECTION:
        thread = threading.Thread(target=thread_function)
        thread.start()
        # wait a bit in case the task is quick, in that case we can reduce flickering in the UI
        try:
            thread.join(timeout=0.5)
        except TimeoutError:
            # if the task is still running, we return the collection without waiting
            pass
        else:
            collection.refresh_from_db()

    return collection


def prepare_collection(
    collection: DataCollection, settings: CreateCollectionSettings, user: User
) -> DataCollection:
    if settings.auto_set_filters:
        prompt = query_language_prompt.replace("{{ query }}", settings.user_input or "")
        settings.result_language = Mistral_Ministral3b().generate_short_text(prompt, exact_required_length=2, temperature=0.3) or "en"
    if settings.workflow_id == Workflows.CLASSIC_SEARCH:
        prepare_for_classic_search(collection, settings, user)
    elif settings.workflow_id == Workflows.ASSISTED_SEARCH:
        prepare_for_assisted_search(collection, settings, user)
    elif settings.workflow_id == Workflows.FACT_FROM_SINGLE_DOCUMENT:
        prepare_for_question(collection, settings, user)
    elif settings.workflow_id == Workflows.FACT_FROM_SINGLE_DOCUMENT:
        # TODO: different implementation
        prepare_for_question(collection, settings, user)
    elif settings.workflow_id == Workflows.OVERVIEW_MAP:
        prepare_for_overview_map(collection, settings, user)
    elif settings.workflow_id == Workflows.RESEARCH_AGENT:
        run_research_agent_in_collection(collection, settings, user)
    elif settings.workflow_id == Workflows.SHOW_ALL:
        prepare_for_show_all_map(collection, settings, user)
    elif settings.workflow_id == Workflows.EMPTY_COLLECTION:
        # nothing to do
        collection.agent_is_running = False
        collection.save()
    else:
        logging.warning(f"Requested unsupported workflow: {settings.workflow_id}")
        collection.agent_is_running = False
        collection.save()
    return collection


def prepare_for_classic_search(collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
    assert settings.user_input is not None
    search_task = SearchTaskSettings(
        dataset_id=settings.dataset_id,
        user_input=settings.user_input or "",
        result_language=settings.result_language,
        auto_set_filters=settings.auto_set_filters,
        filters=settings.filters,
        retrieval_mode=settings.retrieval_mode,
        ranking_settings=settings.ranking_settings,
    )
    run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
    collection.agent_is_running = False
    collection.save()  # 7 ms


def prepare_for_show_all_map(collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
    if settings.filters is None:
        settings.filters = []
    dataset = Dataset.objects.select_related("schema").get(id=settings.dataset_id)
    if dataset.schema.all_parents:
        settings.filters.append(Filter(
            field='_all_parents',
            dataset_id=settings.dataset_id,
            value="",
            operator='is_empty',
            label="Only top-level items",
        ).model_dump())
    search_task = SearchTaskSettings(
        dataset_id=settings.dataset_id,
        user_input=settings.user_input or "",
        result_language=settings.result_language,
        auto_set_filters=False,
        filters=settings.filters,
        retrieval_mode='keyword',
        ranking_settings=settings.ranking_settings,
        candidates_per_step=10,
    )
    run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
    collection.agent_is_running = False
    collection.save()


def prepare_for_overview_map(collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
    assert settings.user_input is not None
    collection.ui_settings = CollectionUiSettings(secondary_view="map", show_visibility_filters=True).model_dump()
    collection.save(update_fields=["ui_settings"])
    search_task = SearchTaskSettings(
        dataset_id=settings.dataset_id,
        user_input=settings.user_input or "",
        result_language=settings.result_language,
        auto_set_filters=settings.auto_set_filters,
        filters=settings.filters,
        retrieval_mode=settings.retrieval_mode,
        ranking_settings=settings.ranking_settings,
        candidates_per_step=2000,
    )
    run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
    collection.agent_is_running = False
    collection.save(update_fields=["agent_is_running"])


def prepare_for_assisted_search(collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
    assert settings.user_input is not None
    create_relevance_column(collection, settings.user_input, settings.result_language)

    search_task = SearchTaskSettings(
        dataset_id=settings.dataset_id,
        user_input=settings.user_input or "",
        result_language=settings.result_language,
        auto_set_filters=settings.auto_set_filters,
        filters=settings.filters,
        retrieval_mode=settings.retrieval_mode,
        ranking_settings=settings.ranking_settings,
    )
    run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
    collection.agent_is_running = False
    collection.save()


def prepare_for_question(collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
    logging.warning("prepare_for_question: start")
    assert settings.user_input is not None
    create_relevance_column(collection, settings.user_input, settings.result_language)

    search_task = SearchTaskSettings(
        dataset_id=settings.dataset_id,
        user_input=settings.user_input or "",
        result_language=settings.result_language,
        auto_set_filters=settings.auto_set_filters,
        filters=settings.filters,
        retrieval_mode=settings.retrieval_mode,
        ranking_settings=settings.ranking_settings,
        auto_approve=False,
        approve_using_comparison=True,
        exit_search_mode=True,
        max_selections=10,
    )

    writing_task = WritingTask(
        collection=collection,
        class_name="_default",
        name="Answer",
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS, COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS],
        use_all_items=True,
        module="Mistral_Mistral_Large",
    )
    writing_task.prompt = settings.user_input
    writing_task.save()
    collection.ui_settings = CollectionUiSettings(secondary_view="summary").model_dump()
    collection.save(update_fields=["ui_settings"])

    def after_columns_were_processed(new_items):
        logging.warning("prepare_for_question: after_columns_were_processed")
        collection.current_agent_step = "Executing writing task..."
        execute_writing_task_thread(writing_task)
        collection.log_explanation(f"Read approved items and **wrote a summary** using an LLM", save=False)
        collection.agent_is_running = False
        collection.save()

    run_search_task(collection, search_task, user.id, after_columns_were_processed, is_new_collection=True)  # type: ignore
    collection.current_agent_step = "Waiting for search results and columns..."
    collection.save(update_fields=["current_agent_step"])
