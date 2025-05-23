import json

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI

import workflows.available_workflows.base_workflows
import workflows.available_workflows.map_workflows
import workflows.available_workflows.question_workflows
import workflows.available_workflows.search_workflows
from data_map_backend.models import DataCollection, Dataset, User
from data_map_backend.notifier import default_notifier
from data_map_backend.schemas import CollectionIdentifier
from data_map_backend.serializers import CollectionSerializer

# need to be loaded somewhere (after Django apps where loaded, therfore not in __init__.py)
from workflows.available_workflows.agents import (
    exhaustive_search,
    exhaustive_search_with_answer,
    research_agent,
)
from workflows.logic import create_collection_using_workflow, workflows_by_id
from workflows.schemas import (
    AvailableWorkflowsPaylaod,
    CreateCollectionSettings,
    WorkflowMetadata,
)

api = NinjaAPI(urls_namespace="workflows")


@api.post("get_available_workflows")
def get_available_workflows_route(request: HttpRequest, payload: AvailableWorkflowsPaylaod):
    try:
        dataset = Dataset.objects.select_related("schema").get(id=payload.dataset_id)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)
    # TODO: check permissions

    highlighted_workflows: list[str] = dataset.merged_advanced_options.get("highlighted_workflows", [])
    available_workflows: list[dict] = dataset.merged_advanced_options.get("available_workflows", [])
    excluded_workflows: list[str] = dataset.merged_advanced_options.get("excluded_workflows", [])
    opt_in_workflows: list[str] = dataset.merged_advanced_options.get("opt_in_workflows", [])

    available_workflow_metadata: list[WorkflowMetadata] = []
    for highlighted_workflow_id in highlighted_workflows:
        if highlighted_workflow_id in workflows_by_id:
            workflow_cls = workflows_by_id[highlighted_workflow_id]
            available_workflow_metadata.append(workflow_cls.metadata)

    additional_workflows = []
    for workflow_cls in workflows_by_id.values():
        if workflow_cls.metadata.workflow_id in highlighted_workflows:
            continue
        if workflow_cls.metadata.workflow_id in excluded_workflows:
            continue
        if available_workflows and workflow_cls.metadata.workflow_id not in available_workflows:
            continue
        if workflow_cls.metadata.needs_opt_in and workflow_cls.metadata.workflow_id not in opt_in_workflows:
            continue
        additional_workflows.append(workflow_cls.metadata)

    additional_workflows = sorted(additional_workflows, key=lambda x: x.order)
    available_workflow_metadata.extend(additional_workflows)

    return available_workflow_metadata


@api.post("create_collection")
def create_collection_route(request: HttpRequest, payload: CreateCollectionSettings):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    assert isinstance(request.user, User)
    collection = create_collection_using_workflow(request.user, payload)
    default_notifier.info(
        f"Running workflow {payload.workflow_id} for user input '{payload.user_input}'", request.user
    )

    dataset_dict = CollectionSerializer(instance=collection).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type="application/json")


@api.post("cancel_agent")
def cancel_agent_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only("created_by", "cancel_agent_flag").get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    collection.cancel_agent_flag = True
    collection.save(update_fields=["cancel_agent_flag"])

    return HttpResponse(status=204)
