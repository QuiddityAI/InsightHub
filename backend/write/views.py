import json
import logging

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI

from data_map_backend.models import (
    COLUMN_META_SOURCE_FIELDS,
    DataCollection,
    WritingTask,
)
from data_map_backend.schemas import CollectionIdentifier
from data_map_backend.serializers import WritingTaskSerializer
from write.logic.writing_task import execute_writing_task_thread
from write.schemas import (
    AddWritingTaskPayload,
    UpdateWritingTaskPayload,
    WritingTaskIdentifier,
)

api = NinjaAPI(urls_namespace="write")


@api.post("get_writing_tasks")
def get_writing_tasks_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only("created_by").get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    tasks = WritingTask.objects.filter(collection_id=payload.collection_id, class_name=payload.class_name)
    tasks = tasks.order_by("created_at")

    task_ids = [{"id": task.id, "name": task.name} for task in tasks]

    return HttpResponse(json.dumps(task_ids), content_type="application/json", status=200)


@api.post("add_writing_task")
def add_writing_task_route(request: HttpRequest, paylaod: AddWritingTaskPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only("created_by").get(id=paylaod.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    task = WritingTask(
        collection_id=paylaod.collection_id,
        class_name=paylaod.class_name,
        name=paylaod.name,
        model="Mistral_Mistral_Large",  # might be overwritten by options
        source_fields=[
            COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
            COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS,
        ],  # might be overwritten by options
    )
    if paylaod.options:
        for key, value in paylaod.options.items():
            setattr(task, key, value)
    task.save()

    if paylaod.run_now:
        execute_writing_task_thread(task)

    data = WritingTaskSerializer(task).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


@api.post("get_writing_task_by_id")
def get_writing_task_by_id_route(request, payload: WritingTaskIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        task = WritingTask.objects.select_related("collection").get(id=payload.task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    data = WritingTaskSerializer(task).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@api.post("delete_writing_task")
def delete_writing_task_route(request, payload: WritingTaskIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        task = WritingTask.objects.select_related("collection").get(id=payload.task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    task.delete()
    return HttpResponse(None, status=204)


@api.post("update_writing_task")
def update_writing_task_route(request: HttpRequest, payload: UpdateWritingTaskPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        task = WritingTask.objects.select_related("collection").get(id=payload.task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    task.name = payload.name
    task.source_fields = payload.source_fields
    task.use_all_items = payload.use_all_items
    task.selected_item_ids = payload.selected_item_ids
    task.model = payload.model
    task.parameters = payload.parameters
    if payload.expression is not None:
        task.expression = payload.expression
    if payload.prompt_template is not None:
        task.prompt_template = payload.prompt_template
    if payload.text is not None and payload.text != task.text:
        if not task.previous_versions:
            task.previous_versions = []
        task.previous_versions.append(
            {
                "created_at": task.changed_at.isoformat(),
                "text": task.text,
                "additional_results": task.additional_results,
            }
        )
        if len(task.previous_versions) > 3:
            task.previous_versions = task.previous_versions[-3:]
        task.text = payload.text
    task.save()

    return HttpResponse(None, status=204)


@api.post("revert_writing_task")
def revert_writing_task_route(request: HttpRequest, payload: WritingTaskIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        task = WritingTask.objects.select_related("collection").get(id=payload.task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    if not task.previous_versions:
        return HttpResponse(status=400)

    last_version = task.previous_versions.pop()
    task.text = last_version["text"]
    task.additional_results = last_version["additional_results"]
    task.save()

    return HttpResponse(None, status=204)


@api.post("execute_writing_task")
def execute_writing_task_route(request: HttpRequest, payload: WritingTaskIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        task = WritingTask.objects.select_related("collection").get(id=payload.task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    execute_writing_task_thread(task)

    return HttpResponse(None, status=204)
