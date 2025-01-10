import time

from llmonkey.llms import Google_Gemini_Flash_1_5_v1

from data_map_backend.models import DataCollection, User, COLUMN_META_SOURCE_FIELDS, WritingTask, CollectionColumn, FieldType
from data_map_backend.schemas import CollectionUiSettings
from search.schemas import SearchTaskSettings
from search.logic.execute_search import run_search_task
from write.logic.writing_task import execute_writing_task_safe
from .schemas import CreateCollectionSettings
from columns.logic.process_column import process_cells_blocking


def run_research_agent_in_collection(collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
    assert settings.user_input is not None

    # run a search:
    collection.current_agent_step = "Searching..."
    collection.save(update_fields=["current_agent_step"])
    time.sleep(2)  # just for the demo to understand the process

    search_task = SearchTaskSettings(
        dataset_id=settings.dataset_id,
        user_input=settings.user_input or "",  # this is the full, natural language question (of course your agent could first generate a better one)
        query=None,  # this is the query used for keyword search, if auto_set_filters is set, its generated automatically
        result_language=settings.result_language,
        auto_set_filters=settings.auto_set_filters,
        filters=settings.filters,
        retrieval_mode=settings.retrieval_mode,
        ranking_settings=settings.ranking_settings,
        auto_approve=False,
        approve_using_comparison=False,
        exit_search_mode=False,
        candidates_per_step=10,  # this is the number of search results
    )
    new_items = run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
    # now the results are already there (search is run synchronously, but if there would already be columns, they are run asynchronously)

    time.sleep(2)  # just for the demo to understand the process

    # create a column:
    column = CollectionColumn.objects.create(
        collection=collection,
        name="Relevance",
        identifier="relevance",  # any unique string
        field_type=FieldType.STRING,
        expression=f"Is the item relevant to the question '{settings.user_input}'?",
        prompt_template=None,  # set this if you want to use a custom prompt, otherwise a default is used
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS, COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS],
        module='llm',  # there is also a special 'relevance' module, but that's a different story
        parameters={'model': Google_Gemini_Flash_1_5_v1.__name__, 'language': settings.result_language},
        auto_run_for_candidates=True,  # set this to run this column for all search results
    )
    time.sleep(2)  # just for the demo to understand the process
    # new_items = collection.items.all()  # alternative to get all items
    max_evaluated_candidates = 10
    collection.current_agent_step = "Evaluating results..."
    collection.log_explanation(f"Evaluting items individually", save=False)
    collection.save(update_fields=["current_agent_step", "explanation_log"])
    process_cells_blocking(new_items[:max_evaluated_candidates], column, collection, user.id)  # type: ignore

    time.sleep(2)  # just for the demo to understand the process

    # create the final result:
    writing_task = WritingTask(
        collection=collection,
        name="Final Answer",
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS, COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS],
        use_all_items=True,
        module="Mistral_Mistral_Large",
        prompt=f"Summarize the results of the search in regard to this question '{settings.user_input}'."
        # its always using a default prompt plus this prompt, I just realized it doesn't have the option to override the default prompt yet
    )
    writing_task.save()
    collection.ui_settings = CollectionUiSettings(secondary_view="summary").model_dump()
    collection.current_agent_step = "Writing final answer..."
    collection.save(update_fields=["ui_settings", "current_agent_step"])
    execute_writing_task_safe(writing_task)
    collection.agent_is_running = False
    collection.save(update_fields=["agent_is_running"])
