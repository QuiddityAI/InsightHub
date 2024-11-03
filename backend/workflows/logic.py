from enum import StrEnum
import threading
import time
import logging

from django.utils import timezone
from llmonkey.llms import Mistral_Ministral3b

from data_map_backend.models import DataCollection, User, COLUMN_META_SOURCE_FIELDS, WritingTask
from search.schemas import SearchTaskSettings
from search.logic.execute_search import run_search_task
from data_map_backend.views.question_views import _execute_writing_task_thread
from .schemas import CreateCollectionSettings
from .create_columns import create_relevance_column
from workflows.prompts import query_language_prompt


class CollectionCreationModes(StrEnum):
    ASSISTED_SEARCH = 'assisted_search'
    CLASSIC_SEARCH = 'classic_search'
    QUESTION = 'question'
    OVERVIEW_MAP = 'overview_map'
    EMPTY_COLLECTION = 'empty_collection'


def create_collection_using_mode(
    user: User, settings: CreateCollectionSettings
) -> DataCollection:
    collection = DataCollection()
    collection.created_by = user
    collection.name = settings.user_input or f"Collection {timezone.now().isoformat()}"
    collection.related_organization_id = settings.related_organization_id  # type: ignore
    collection.agent_is_running = settings.mode != CollectionCreationModes.EMPTY_COLLECTION
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

    if settings.mode != CollectionCreationModes.EMPTY_COLLECTION:
        threading.Thread(target=thread_function).start()

    return collection


def prepare_collection(
    collection: DataCollection, settings: CreateCollectionSettings, user: User
) -> DataCollection:
    if settings.auto_set_filters:
        prompt = query_language_prompt.replace("{{ query }}", settings.user_input or "")
        settings.result_language = Mistral_Ministral3b().generate_short_text(prompt, exact_required_length=2, temperature=0.3) or "en"
    if settings.mode == CollectionCreationModes.CLASSIC_SEARCH:
        prepare_for_classic_search(collection, settings, user)
    elif settings.mode == CollectionCreationModes.ASSISTED_SEARCH:
        prepare_for_assisted_search(collection, settings, user)
    elif settings.mode == CollectionCreationModes.OVERVIEW_MAP:
        prepare_for_overview_map(collection, settings, user)
    elif settings.mode == CollectionCreationModes.QUESTION:
        prepare_for_question(collection, settings, user)
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


def prepare_for_overview_map(collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
    assert settings.user_input is not None
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
    collection.save()  # 7 ms


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
        auto_approve=True,
        exit_search_mode=True,
        max_selections=3,
    )

    writing_task = WritingTask(
        collection=collection,
        class_name="_default",
        name="Answer",
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS, COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS],
        use_all_items=True,
        #module="groq_llama_3_70b",
        module="openai_gpt_4_o",
    )
    writing_task.prompt = settings.user_input
    writing_task.save()

    def after_columns_were_processed(new_items):
        logging.warning("prepare_for_question: after_columns_were_processed")
        collection.current_agent_step = "Executing writing task..."
        _execute_writing_task_thread(writing_task)
        collection.log_explanation(f"Read approved items and **wrote a summary** using an LLM", save=False)
        collection.agent_is_running = False
        collection.save()

    run_search_task(collection, search_task, user.id, after_columns_were_processed, is_new_collection=True)  # type: ignore
    collection.current_agent_step = "Waiting for search results and columns..."
