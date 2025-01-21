from enum import StrEnum
from typing import Optional

from ninja import Schema


class WorkflowOrder:
    search = 100
    question = 200
    agent = 300
    map = 400
    other = 500
    base = 900


class AvailableWorkflowsPaylaod(Schema):
    dataset_id: int


class WorkflowAvailability(StrEnum):
    general_availability = "general_availability"
    preview = "preview"
    in_development = "in_development"


class WorkflowMetadata(Schema):
    workflow_id: str
    order: int = 9999
    name1: dict = {"en": "Unnamed"}  # most fields can use <entity_name_singular> and <entity_name_plural> placeholders
    name2: dict = {"en": "Workflow"}  # name1 is the upper part in the UI, name2 is the main part
    help_text: dict = {"en": ""}
    query_field_hint: dict = {"en": "Your input"}
    supports_filters: bool = False
    supports_user_input: bool = True
    needs_user_input: bool = True
    needs_result_language: bool = True
    availability: str = WorkflowAvailability.general_availability
    needs_opt_in: bool = True


class CreateCollectionSettings(Schema):
    related_organization_id: int
    dataset_id: int
    workflow_id: str
    auto_set_filters: bool
    filters: Optional[list]
    user_input: Optional[str]
    result_language: Optional[str]
    retrieval_mode: Optional[str]
    ranking_settings: Optional[dict]
