from django.contrib.auth.models import User

from data_map_backend.models import DataCollection, Dataset
from search.schemas import SearchTaskSettings, Filter
from search.logic.execute_search import run_search_task
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata, WorkflowAvailability, WorkflowOrder
from workflows.logic import WorkflowBase, workflow


@workflow
class EmptyCollectionWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="empty_collection",
        order=WorkflowOrder.base + 90,  # usually the last one
        name1="Empty Collection",
        name2="For Notes and Documents",
        help_text="Create an empty collection to collect notes or documents",
        query_field_hint="Name of the collection",
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
        order=WorkflowOrder.base + 1,
        name1="Show",
        name2="All <entity_name_plural>",
        help_text="Show all top-level items (e.g. to navigate through the folder hierarchy)",
        query_field_hint="Name of the collection",
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
