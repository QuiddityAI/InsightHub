from django.contrib.auth.models import User

from data_map_backend.models import DataCollection
from workflows.logic import WorkflowBase, workflow
from workflows.schemas import (
    CreateCollectionSettings,
    WorkflowAvailability,
    WorkflowCategory,
    WorkflowMetadata,
    WorkflowOrder,
)


@workflow
class TimelineWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="timeline",
        categories=[WorkflowCategory.answer_and_report],
        order=WorkflowOrder.other + 1,
        name1={"en": "Create a", "de": "Erstelle eine"},
        name2={"en": "Timeline of Events", "de": "Zeitleiste der Ereignisse"},
        help_text={
            "en": "Find specific events in <entity_name_plural> and show a timeline",
            "de": "Finde spezifische Ereignisse in <entity_name_plural> und zeige eine Zeitleiste",
        },
        query_field_hint={"en": "Your question", "de": "Deine Frage"},
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.in_development,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        collection.agent_is_running = False
        collection.save(update_fields=["agent_is_running"])
