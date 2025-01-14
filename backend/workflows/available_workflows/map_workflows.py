from django.contrib.auth.models import User

from data_map_backend.models import DataCollection
from data_map_backend.schemas import CollectionUiSettings
from search.schemas import SearchTaskSettings, SearchType
from search.logic.execute_search import run_search_task
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata, WorkflowOrder, WorkflowAvailability
from workflows.logic import WorkflowBase, workflow


@workflow
class OverviewMapWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="overview_map",
        order=WorkflowOrder.map + 1,
        name1="Show a visual",
        name2="Overview Map of <entity_name_plural>",
        help_text="Show a large set of items on a visual map",
        query_field_hint="Describe what <entity_name_plural> you want to find",
        supports_filters=True,
        needs_user_input=False,
        needs_result_language=True,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        collection.ui_settings = CollectionUiSettings(secondary_view="map", show_visibility_filters=True).model_dump()
        collection.save(update_fields=["ui_settings"])
        if settings.user_input:
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
        else:
            collection.name = "Overview Map"
            collection.save(update_fields=["name"])
            search_task = SearchTaskSettings(
                search_type=SearchType.RANDOM_SAMPLE,
                dataset_id=settings.dataset_id,
                user_input="Random Sample / All Items",
                result_language=settings.result_language,
                auto_set_filters=False,
                filters=settings.filters,
                retrieval_mode=settings.retrieval_mode,
                ranking_settings=settings.ranking_settings,
                candidates_per_step=2000,
            )
        run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
        collection.agent_is_running = False
        collection.save(update_fields=["agent_is_running"])
