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
from search.logic.execute_search import run_search_task
from write.logic.writing_task import execute_writing_task_thread
from workflows.schemas import CreateCollectionSettings, WorkflowMetadata, WorkflowAvailability, WorkflowOrder
from workflows.create_columns import create_relevance_column
from workflows.logic import WorkflowBase, workflow


@workflow
class TimelineWorkflow(WorkflowBase):
    metadata: WorkflowMetadata = WorkflowMetadata(
        workflow_id="timeline",
        order=WorkflowOrder.other + 1,
        name1="Create a",
        name2="Timeline of Events",
        help_text="Find specific events in <entity_name_plural> and show a timeline",
        query_field_hint="Your question",
        supports_filters=True,
        needs_user_input=True,
        needs_result_language=True,
        availability=WorkflowAvailability.in_development,
    )

    def run(self, collection: DataCollection, settings: CreateCollectionSettings, user: User) -> None:
        collection.agent_is_running = False
        collection.save(update_fields=["agent_is_running"])
