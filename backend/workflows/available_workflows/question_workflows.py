import logging

from data_map_backend.models import (
    COLUMN_META_SOURCE_FIELDS,
    DataCollection,
    User,
    WritingTask,
)
from data_map_backend.schemas import CollectionUiSettings
from search.logic.execute_search import create_and_run_search_task
from search.schemas import SearchTaskSettings
from workflows.create_columns import create_relevance_column
from workflows.logic import WorkflowBase, workflow
from workflows.schemas import (
    CreateCollectionSettings,
    WorkflowAvailability,
    WorkflowMetadata,
    WorkflowOrder,
)
from write.logic.writing_task import execute_writing_task_thread


@workflow
class FindFactFromSingleDocumentWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="fact_from_single_document",
        order=WorkflowOrder.question + 1,
        name1={"en": "Find a", "de": "Finde einen"},
        name2={"en": "Fact in a <entity_name_singular>", "de": "Fakt in Dokumenten"},
        help_text={
            "en": "For questions that can be answered based on one item",
            "de": "Für Fragen, die anhand eines Dokuments beantwortet werden können",
        },
        query_field_hint={"en": "Your question", "de": "Deine Frage"},
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        assert settings.user_input is not None
        create_relevance_column(collection, settings.user_input, settings.result_language, user)

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
            forced_selections=1,
            max_selections=10,
        )

        writing_task = WritingTask(
            collection=collection,
            class_name="_default",
            name="Answer",
            source_fields=[
                COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
                COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
            ],
            use_all_items=True,
            module=user.preferences.get("default_large_llm") or "Mistral_Mistral_Large",
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

        create_and_run_search_task(collection, search_task, user.id, after_columns_were_processed, is_new_collection=True)  # type: ignore
        collection.current_agent_step = "Waiting for search results and columns..."
        collection.save(update_fields=["current_agent_step"])


@workflow
class CollectFactsFromMultipleDocumentsWorkflow(FindFactFromSingleDocumentWorkflow):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="facts_from_multiple_documents",
        order=WorkflowOrder.question + 2,
        name1={"en": "Collect Facts", "de": "Sammle Fakten"},
        name2={"en": "From Multiple <entity_name_plural>", "de": "Aus mehreren Dokumenten"},
        help_text={
            "en": "Collect information found in multiple documents",
            "de": "Sammle Informationen aus mehreren Dokumenten",
        },
        query_field_hint={"en": "Your question", "de": "Deine Frage"},
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
        name1={"en": "Write a report", "de": "Bericht über"},
        name2={"en": "Beyond individual Facts", "de": "einzelne Fakten hinaus"},
        help_text={
            "en": "E.g. analyze the status and history of a project",
            "de": "Z.B. um den Status und die Geschichte eines Projekts zu analysieren",
        },
        query_field_hint={"en": "Your question", "de": "Deine Frage"},
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.in_development,
        needs_opt_in=False,
    )

    # TODO: currently uses the same logic as FindFactFromSingleDocumentWorkflow
