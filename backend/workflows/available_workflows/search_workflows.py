from django.contrib.auth.models import User

from data_map_backend.models import DataCollection
from search.schemas import SearchTaskSettings
from search.logic.execute_search import run_search_task
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata, WorkflowOrder, WorkflowAvailability
from workflows.create_columns import create_relevance_column
from workflows.logic import WorkflowBase, workflow


@workflow
class ClassicSearchWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="classic_search",
        order=WorkflowOrder.search + 1,
        name1="Find a single",
        name2="Known <entity_name_singular>",
        help_text="Fast + accurate search",
        query_field_hint="Describe what <entity_name_singular> you want to find",
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
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


@workflow
class AssistedSearchWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="assisted_search",
        order=WorkflowOrder.search + 2,
        name1="Find a set of",
        name2="Matching <entity_name_plural>",
        help_text="Search + evaluate every single result, good to collect a set of <entity_name_plural>",
        query_field_hint="Describe what <entity_name_plural> you want to find",
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
        )
        run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
        collection.agent_is_running = False
        collection.save()
