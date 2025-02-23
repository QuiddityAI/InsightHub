import logging

import dspy

from config.utils import get_default_model
from data_map_backend.models import CollectionColumn, DataCollection, Dataset, User
from workflows.available_workflows.agents.agent_api import QuiddityAgentAPI
from workflows.available_workflows.agents.utils import override_dspy_model
from workflows.available_workflows.buiilding_blocks.exhaustive_search_bb import (
    ExhaustiveSearchBB,
)
from workflows.dspy_models import register_dspy_model
from workflows.logic import WorkflowBase, workflow
from workflows.schemas import (
    CreateCollectionSettings,
    WorkflowAvailability,
    WorkflowCategory,
    WorkflowMetadata,
    WorkflowOrder,
)

dspy_lm = dspy.LM(**get_default_model("medium").to_litellm())


@workflow
class ExhaustiveSearchWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="exhaustive_search",
        order=WorkflowOrder.agent + 2,
        categories=[WorkflowCategory.search_and_curate],
        name1={"en": "🕵️ Let an", "de": "🕵️ Lass einen"},
        name2={"en": "Agent find relevant docs", "de": "relevanten Dokumente finden"},
        help_text={
            "en": "An agent that looks for documents relevant to your query",
            "de": "Ein Agent, der nach Dokumenten sucht, die für deine Anfrage relevant sind",
        },
        query_field_hint={
            "en": "What <entity_name_plural> you want to find",
            "de": "Welche <entity_name_plural> möchtest Du finden?",
        },
        supports_filters=False,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.general_availability,
        needs_opt_in=False,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        assert settings.user_input is not None

        dataset = Dataset.objects.get(id=settings.dataset_id)
        total_items: int = dataset.item_count or 100  # type: ignore
        # set parameters for the exhaustive search based on the dataset size
        params_per_size = {  # TODO: for small dataset use true exhaustive search
            100: dict(max_depth=2, max_queries=3),
            250: dict(max_depth=3, max_queries=4),
            500: dict(max_depth=3, max_queries=5),
            1000: dict(max_depth=7, max_queries=7),
        }

        selected_params = None
        for size in sorted(params_per_size.keys()):
            if total_items <= size:
                selected_params = params_per_size[size]
                break

        if selected_params is None:
            selected_params = params_per_size[max(params_per_size.keys())]

        api = QuiddityAgentAPI(collection, settings, user)

        search_bb = ExhaustiveSearchBB(dspy_lm=dspy_lm, explore_around_rare=False, **selected_params, learn_query=True)
        collection, out_context = search_bb(api, collection, search_bb.InputContext(user_input=settings.user_input))

        api.exit_search_mode()
        api.set_agent_running(False)
