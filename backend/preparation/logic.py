from enum import StrEnum
import threading
import time

from django.utils import timezone

from data_map_backend.models import DataCollection, User, COLUMN_META_SOURCE_FIELDS, WritingTask
from search.schemas import SearchTaskSettings
from search.logic import run_search_task
from data_map_backend.views.question_views import _execute_writing_task_thread
from .schemas import CreateCollectionSettings
from .create_columns import create_relevance_column


class CollectionCreationModes(StrEnum):
    QUICK_SEARCH = 'quick_search'
    QUESTION = 'question'
    EMPTY_COLLECTION = 'empty_collection'


def create_collection_using_mode(
    user: User, settings: CreateCollectionSettings
) -> DataCollection:
    item = DataCollection()
    item.created_by = user
    item.name = settings.query or f"Collection {timezone.now().isoformat()}"
    item.related_organization_id = settings.related_organization_id  # type: ignore
    item.agent_is_running = settings.mode != CollectionCreationModes.EMPTY_COLLECTION
    item.current_agent_step = "Preparing..."
    item.cancel_agent_flag = False
    item.save()

    def thread_function():
        try:
            prepare_collection(item, settings)
        finally:
            item.agent_is_running = False
            item.save()

    if settings.mode != CollectionCreationModes.EMPTY_COLLECTION:
        threading.Thread(target=thread_function).start()

    return item


def prepare_collection(
    collection: DataCollection, settings: CreateCollectionSettings
) -> DataCollection:
    if settings.mode == CollectionCreationModes.QUICK_SEARCH:
        prepare_for_quick_search(collection, settings)
    elif settings.mode == CollectionCreationModes.QUESTION:
        prepare_for_question(collection, settings)
    return collection


def prepare_for_quick_search(collection: DataCollection, settings: CreateCollectionSettings) -> None:
    assert settings.query is not None
    create_relevance_column(collection, settings.query)

    search_task = SearchTaskSettings(
        dataset_id=settings.dataset_id,
        query=settings.query,
        result_language=settings.result_language,
        auto_set_filters=settings.auto_set_filters,
        filters=settings.filters,
        retrieval_mode=settings.retrieval_mode,
        ranking_settings=settings.ranking_settings,
    )
    run_search_task(collection, search_task)


def prepare_for_question(collection: DataCollection, settings: CreateCollectionSettings) -> None:
    prepare_for_quick_search(collection, settings)
    # TODO: auto-approve candidates
    # TODO: exit search mode

    writing_task = WritingTask(
        collection=collection,
        class_name="_default",
        name="Answer",
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS],
        use_all_items=True,
        module="groq_llama_3_70b",
    )
    writing_task.prompt = settings.query
    writing_task.save()
    time.sleep(2)
    _execute_writing_task_thread(writing_task)
