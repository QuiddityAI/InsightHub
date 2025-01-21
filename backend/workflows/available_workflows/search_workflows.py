from data_map_backend.models import DataCollection, User
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


@workflow
class ClassicSearchWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="classic_search",
        order=WorkflowOrder.search + 1,
        name1={"en": "Find a single", "de": "Finde einzelne"},
        name2={
            "en": "Known <entity_name_singular>",
            "de": "Bekannte <entity_name_plural>",
        },  # using plural in German to not care about word gender
        help_text={"en": "Fast + accurate search", "de": "Schnelle + genaue Suche"},
        query_field_hint={
            "en": "Describe what <entity_name_singular> you want to find",
            "de": "Beschreibe, welche <entity_name_plural> du finden möchtest",
        },
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
        create_and_run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
        collection.agent_is_running = False
        collection.save()  # 7 ms


@workflow
class AssistedSearchWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="assisted_search",
        order=WorkflowOrder.search + 2,
        name1={"en": "Find a set of", "de": "Finde mehrere"},
        name2={"en": "Matching <entity_name_plural>", "de": "Passende <entity_name_plural>"},
        help_text={
            "en": "Evaluates every result separately, good to collect a set of <entity_name_plural>",
            "de": "Evaluiert jedes Ergebnis einzeln. Sinnvoll um mehrere <entity_name_plural> zu sammeln.",
        },
        query_field_hint={
            "en": "Describe what <entity_name_plural> you want to find",
            "de": "Beschreibe, welche <entity_name_plural> du finden möchtest",
        },
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
        )
        create_and_run_search_task(collection, search_task, user.id, is_new_collection=True)  # type: ignore
        collection.agent_is_running = False
        collection.save()
