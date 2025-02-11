import json
import logging
import threading

from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI

from data_map_backend.models import CollectionItem, DataCollection, Dataset, SearchTask
from data_map_backend.notifier import default_notifier
from data_map_backend.schemas import CollectionIdentifier, ItemRelevance
from data_map_backend.serializers import SearchTaskSerializer
from legacy_backend.database_client.text_search_engine_client import (
    TextSearchEngineClient,
)
from search.logic.approve_items_and_exit_search import (
    approve_relevant_search_results,
    exit_search_mode,
)
from search.logic.execute_search import (
    add_items_from_task_and_run_columns,
    create_and_run_search_task,
    run_search_task,
)
from search.logic.notify_about_new_items import notify_about_new_items
from search.schemas import (
    GetPlainResultsPaylaod,
    RunExistingSearchTaskPayload,
    RunPreviousSearchTaskPayload,
    RunSearchTaskPayload,
    TestNotificationEmailPayload,
    UpdateSearchTaskExecutionSettingsPayload,
)

api = NinjaAPI(urls_namespace="search")


@api.post("run_search_task")
def run_search_task_route(request: HttpRequest, payload: RunSearchTaskPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    collection.agent_is_running = True
    collection.current_agent_step = "Running search task..."
    collection.save(update_fields=["agent_is_running", "current_agent_step"])
    default_notifier.info(f"Running search task for user input '{payload.search_task.user_input}'", request.user)

    def thread_function():
        try:
            create_and_run_search_task(collection, payload.search_task, request.user.id)  # type: ignore
        finally:
            collection.agent_is_running = False
            collection.current_agent_step = None
            collection.save(update_fields=["agent_is_running", "current_agent_step"])

    thread = threading.Thread(target=thread_function)
    thread.start()
    if payload.wait_for_ms > 0:
        try:
            thread.join(timeout=payload.wait_for_ms / 1000)
        except TimeoutError:
            # if the thread is still running after the timeout, we just let it run
            pass

    return HttpResponse(status=204)


@api.post("perform_search")
def perform_search_route(request: HttpRequest, payload: RunSearchTaskPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    collection.agent_is_running = True
    collection.current_agent_step = "Running search task..."
    collection.save(update_fields=["agent_is_running", "current_agent_step"])

    try:
        results = run_search_task(collection, payload.search_task, request.user.id)  # type: ignore
    finally:
        collection.agent_is_running = False
        collection.current_agent_step = None
        collection.save(update_fields=["agent_is_running", "current_agent_step"])
    results = [model_to_dict(r) for r in results]
    return HttpResponse(json.dumps(results), status=200, content_type="application/json")


@api.post("say_hello")
def say_hello(request):
    return HttpResponse("Hello, World!")


@api.post("run_previous_search_task")
def run_previous_search_task_route(request: HttpRequest, payload: RunPreviousSearchTaskPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    if len(collection.search_task_navigation_history) < 2:
        return HttpResponse(status=400)

    previous_task = SearchTask.objects.get(id=collection.search_task_navigation_history[-2])

    collection.agent_is_running = True
    collection.current_agent_step = "Running search task..."
    collection.search_task_navigation_history = collection.search_task_navigation_history[:-2]
    collection.save(update_fields=["agent_is_running", "current_agent_step", "search_task_navigation_history"])

    def thread_function():
        try:
            run_search_task(previous_task, request.user.id, from_ui=True)  # type: ignore
        finally:
            collection.agent_is_running = False
            collection.current_agent_step = None
            collection.save(update_fields=["agent_is_running", "current_agent_step"])

    thread = threading.Thread(target=thread_function)
    thread.start()
    if payload.wait_for_ms > 0:
        try:
            thread.join(timeout=payload.wait_for_ms / 1000)
        except TimeoutError:
            # if the thread is still running after the timeout, we just let it run
            pass

    return HttpResponse(status=204, content_type="application/json")


@api.post("run_existing_search_task")
def run_existing_search_task_route(request: HttpRequest, payload: RunExistingSearchTaskPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        task = SearchTask.objects.select_related("collection").get(id=payload.task_id)
    except SearchTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:
        return HttpResponse(status=401)

    collection = task.collection

    collection.agent_is_running = True
    collection.current_agent_step = "Running search task..."
    collection.save(update_fields=["agent_is_running", "current_agent_step"])

    def thread_function():
        try:
            run_search_task(task, request.user.id, from_ui=True)  # type: ignore
        finally:
            collection.agent_is_running = False
            collection.current_agent_step = None
            collection.save(update_fields=["agent_is_running", "current_agent_step"])

    thread = threading.Thread(target=thread_function)
    thread.start()
    if payload.wait_for_ms > 0:
        try:
            thread.join(timeout=payload.wait_for_ms / 1000)
        except TimeoutError:
            # if the thread is still running after the timeout, we just let it run
            pass

    return HttpResponse(status=204)


@api.post("add_more_items_from_active_task")
def add_more_items_from_active_task_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.select_related("most_recent_search_task").get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    if not collection.most_recent_search_task:
        return HttpResponse(status=400)

    new_items = add_items_from_task_and_run_columns(
        collection.most_recent_search_task,
        request.user.id,  # type: ignore
        ignore_last_retrieval=False,
        is_new_collection=False,
        from_ui=True,
    )
    result = {"new_item_count": len(new_items)}

    return HttpResponse(json.dumps(result), status=200, content_type="application/json")


@api.post("exit_search_mode")
def exit_search_mode_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only(
            "created_by",
        ).get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    exit_search_mode(collection, payload.class_name, from_ui=True)

    return HttpResponse(status=204, content_type="application/json")


@api.post("approve_relevant_search_results")
def approve_relevant_search_results_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    approve_relevant_search_results(collection, payload.class_name, from_ui=True)

    return HttpResponse(status=204, content_type="application/json")


@api.post("get_plain_results")
def get_plain_results_route(request: HttpRequest, payload: GetPlainResultsPaylaod):
    try:
        dataset = Dataset.objects.get(id=payload.dataset_id)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)
    if payload.access_token not in (dataset.advanced_options or {}).get("access_tokens", {}):
        return HttpResponse(status=401)

    text_db_client = TextSearchEngineClient.get_instance()
    results = text_db_client.get_plain_results(dataset, payload.query_body)

    return HttpResponse(json.dumps(results), status=200, content_type="application/json")


@api.post("update_search_task_execution_settings")
def update_search_task_execution_settings_route(
    request: HttpRequest, payload: UpdateSearchTaskExecutionSettingsPayload
):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        task = SearchTask.objects.select_related("collection__created_by").get(id=payload.task_id)
    except SearchTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:
        return HttpResponse(status=401)

    allowed_keys = {"is_saved", "run_on_new_items"}
    for key, value in payload.updates.items():
        if key not in allowed_keys:
            return HttpResponse(status=400)
        setattr(task, key, value)

    if task.run_on_new_items:
        task.is_saved = True
    task.save(update_fields=list(payload.updates.keys()))

    return HttpResponse(status=204, content_type="application/json")


@api.post("get_saved_search_tasks")
def get_saved_search_tasks_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    tasks = SearchTask.objects.filter(
        Q(is_saved=True) | Q(run_on_new_items=True),
        collection=payload.collection_id,
        collection__created_by=request.user,
    ).order_by("-created_at")
    print(tasks)
    results = SearchTaskSerializer(tasks, many=True).data

    return HttpResponse(json.dumps({"tasks": results}), status=200, content_type="application/json")


@api.post("test_notification_email")
def test_notification_email_route(request: HttpRequest, payload: TestNotificationEmailPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    dataset_id: int | None = None
    if payload.run_on_current_candidates:
        # actually run periodic searches on current candidates:
        dataset_id = collection.first_dataset_id
        if not dataset_id:
            return HttpResponse(status=400, content="No dataset_id found")
        candidates = collection.items.filter(relevance=ItemRelevance.CANDIDATE)
        from legacy_backend.logic.insert_logic import run_periodic_searches

        run_periodic_searches(
            dataset_id, [item.item_id for item in candidates if item.item_id is not None], collection.id
        )
    else:
        # just test with random items:
        possible_items = collection.items.order_by("?").filter(
            dataset_id__isnull=False, relevance__gte=ItemRelevance.APPROVED_BY_AI
        )
        random_item: CollectionItem | None = possible_items.first()
        if not random_item:
            return HttpResponse(status=400, content="No approved items to test with")
        assert random_item.dataset_id is not None
        dataset_id = random_item.dataset_id
        more_items = possible_items.filter(dataset_id=dataset_id)[:3]
        notify_about_new_items(dataset_id, collection, more_items)

    return HttpResponse(status=204)
