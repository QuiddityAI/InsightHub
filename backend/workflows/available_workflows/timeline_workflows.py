from enum import StrEnum
import threading
import time
import logging

from django.utils import timezone
from django.contrib.auth.models import User
from llmonkey.llms import Mistral_Ministral3b

from data_map_backend.models import DataCollection, COLUMN_META_SOURCE_FIELDS, WritingTask, Dataset
from data_map_backend.schemas import CollectionUiSettings
from search.schemas import SearchTaskSettings, Filter
from search.logic.execute_search import create_and_run_search_task
from write.logic.writing_task import execute_writing_task_thread
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata, WorkflowAvailability, WorkflowOrder
from workflows.logic import WorkflowBase, workflow


@workflow
class TimelineWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="timeline",
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
