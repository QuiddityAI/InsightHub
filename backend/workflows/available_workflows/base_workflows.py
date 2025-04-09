from django.contrib.auth.models import User

from data_map_backend.models import DataCollection, Dataset
from search.logic.execute_search import create_and_run_search_task
from search.schemas import Filter, SearchTaskSettings
from workflows.logic import WorkflowBase, workflow
from workflows.schemas import (
    CreateCollectionSettings,
    WorkflowAvailability,
    WorkflowCategory,
    WorkflowMetadata,
    WorkflowOrder,
)


@workflow
class EmptyCollectionWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="empty_collection",
        categories=[WorkflowCategory.store_and_share],
        order=WorkflowOrder.base + 90,  # usually the last one
        name1={"en": "🗒️ Empty Collection", "de": "🗒️ Leere Sammlung"},
        name2={"en": "For Notes and Documents", "de": "Für Notizen und Dokumente"},
        help_text={
            "en": "Create an empty collection to collect notes or documents",
            "de": "Erstelle eine leere Sammlung, um Notizen oder Dokumente zu sammeln",
        },
        query_field_hint={"en": "Name of the collection", "de": "Name der Sammlung"},
        supports_filters=False,
        needs_user_input=False,
        needs_result_language=False,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        collection.agent_is_running = False
        collection.save(update_fields=["agent_is_running"])


@workflow
class ShowAllWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="show_all",
        categories=[WorkflowCategory.search_and_curate, WorkflowCategory.process_and_automate],
        order=WorkflowOrder.base + 1,
        name1={"en": "↕️ Show", "de": "↕️ Zeige"},
        name2={"en": "All <entity_name_plural>", "de": "Alle <entity_name_plural>"},
        help_text={
            "en": "Show all top-level items (e.g. to navigate through a folder hierarchy or show most recent items)",
            "de": "Zeige alle obersten Elemente an (z.B. um durch eine Ordnerhierarchie zu navigieren oder die neuesten Elemente anzuzeigen)",
        },
        query_field_hint={"en": "Name of the collection", "de": "Name der Sammlung"},
        supports_filters=True,
        supports_user_input=False,
        needs_user_input=False,
        needs_result_language=False,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        collection.name = "All items"
        if settings.filters is None:
            settings.filters = []
        dataset = Dataset.objects.select_related("schema").get(id=settings.dataset_id)
        if dataset.schema.all_parents:
            settings.filters.append(
                Filter(
                    field="_all_parents",
                    dataset_id=settings.dataset_id,
                    value="",
                    operator="is_empty",
                    label="Only top-level items",
                ).model_dump()
            )
        search_task = SearchTaskSettings(
            dataset_id=settings.dataset_id,
            user_input=settings.user_input or "",
            result_language=settings.result_language,
            auto_set_filters=settings.auto_set_filters,
            filters=settings.filters,
            retrieval_mode="keyword",  # doesn't matter, no text query
            ranking_settings=settings.ranking_settings,
            candidates_per_step=10,
        )
        create_and_run_search_task(collection, search_task, user, is_new_collection=True)  # type: ignore
        collection.agent_is_running = False
        collection.save()
