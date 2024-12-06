import logging
import json

from django.http import HttpResponse

from ninja import NinjaAPI

from data_map_backend.models import DataCollection, WritingTask
from data_map_backend.serializers import WritingTaskSerializer

from write.logic.writing_task import execute_writing_task_thread

api = NinjaAPI(urls_namespace="write")


@api.post("get_writing_tasks")
def get_writing_tasks_route(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data['collection_id']
        class_name: str = data['class_name']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    tasks = WritingTask.objects.filter(collection_id=collection_id, class_name=class_name)
    tasks = tasks.order_by('created_at')

    task_ids = [{'id': task.id, 'name': task.name} for task in tasks]  # type: ignore

    return HttpResponse(json.dumps(task_ids), content_type="application/json", status=200)


@api.post("add_writing_task")
def add_writing_task_route(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data['collection_id']
        class_name: str = data['class_name']
        name: str = data['name']
        options: dict | None = data.get('options', None)
        run_now: bool = data.get('run_now', False)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    task = WritingTask(
        collection_id=collection_id,
        class_name=class_name,
        name=name,
        module='openai_gpt_4_o',
    )
    if options:
        for key, value in options.items():
            setattr(task, key, value)
    task.save()

    if run_now:
        execute_writing_task_thread(task)

    data = WritingTaskSerializer(task).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


@api.post("get_writing_task_by_id")
def get_writing_task_by_id_route(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    data = WritingTaskSerializer(task).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@api.post("delete_writing_task")
def delete_writing_task_route(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    task.delete()
    return HttpResponse(None, status=204)


@api.post("update_writing_task")
def update_writing_task_route(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
        name: str = data['name']
        source_fields: list = data.get('source_fields', [])
        use_all_items: bool = data.get('use_all_items', True)
        selected_item_ids: list = data.get('selected_item_ids', [])
        module: str | None = data.get('module', None)
        parameters: dict = data.get('parameters', {})
        prompt: str | None = data.get('prompt', None)
        text: str | None = data.get('text', None)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    task.name = name
    task.source_fields = source_fields  # type: ignore
    task.use_all_items = use_all_items
    task.selected_item_ids = selected_item_ids  # type: ignore
    task.module = module
    task.parameters = parameters  # type: ignore
    if prompt is not None:
        task.prompt = prompt
    if text is not None and text != task.text:
        if not task.previous_versions:
            task.previous_versions = []  # type: ignore
        task.previous_versions.append({
            'created_at': task.changed_at.isoformat(),
            'text': task.text,
            'additional_results': task.additional_results,
        })
        if len(task.previous_versions) > 3:
            task.previous_versions = task.previous_versions[-3:]  # type: ignore
        task.text = text
    task.save()

    return HttpResponse(None, status=204)


@api.post("revert_writing_task")
def revert_writing_task_route(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    if not task.previous_versions:
        return HttpResponse(status=400)

    last_version = task.previous_versions.pop()
    task.text = last_version['text']
    task.additional_results = last_version['additional_results']
    task.save()

    return HttpResponse(None, status=204)


@api.post("execute_writing_task")
def execute_writing_task_route(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    execute_writing_task_thread(task)

    return HttpResponse(None, status=204)

