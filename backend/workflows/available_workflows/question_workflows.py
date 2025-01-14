import logging

from django.contrib.auth.models import User

from data_map_backend.models import DataCollection, COLUMN_META_SOURCE_FIELDS, WritingTask
from data_map_backend.schemas import CollectionUiSettings
from search.schemas import SearchTaskSettings
from search.logic.execute_search import run_search_task
from write.logic.writing_task import execute_writing_task_thread
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata, WorkflowOrder, WorkflowAvailability
from workflows.create_columns import create_relevance_column
from workflows.logic import WorkflowBase, workflow


@workflow
class FindFactFromSingleDocumentWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="fact_from_single_document",
        order=WorkflowOrder.question + 1,
        name1="Find a",
        name2="Fact in a <entity_name_singular>",
        help_text="For questions that can be answered based on one document",
        query_field_hint="Your question",
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
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


@workflow
class CollectFactsFromMultipleDocumentsWorkflow(FindFactFromSingleDocumentWorkflow):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="facts_from_multiple_documents",
        order=WorkflowOrder.question + 2,
        name1="Collect Facts",
        name2="From Multiple <entity_name_plural>",
        help_text="Collect information found in multiple documents",
        query_field_hint="Your question",
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.preview,
        needs_opt_in=False,
    )

    # TODO: currently uses the same logic as FindFactFromSingleDocumentWorkflow


@workflow
class BeyondExistingFactsWorkflow(FindFactFromSingleDocumentWorkflow):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="beyond_existing_facts",
        order=WorkflowOrder.question + 3,
        name1="Write a report",
        name2="Beyond individual Facts",
        help_text="E.g. analyze the status and history of a project",
        query_field_hint="Your question",
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.in_development,
        needs_opt_in=False,
    )

    # TODO: currently uses the same logic as FindFactFromSingleDocumentWorkflow
