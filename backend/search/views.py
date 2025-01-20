import json
import threading

from django.http import HttpResponse, HttpRequest
from django.forms.models import model_to_dict
from ninja import NinjaAPI

from data_map_backend.models import DataCollection, Dataset
from data_map_backend.schemas import CollectionIdentifier
from legacy_backend.database_client.text_search_engine_client import TextSearchEngineClient

from search.schemas import (
    RunSearchTaskPayload,
    SearchTaskSettings,
    RunPreviousSearchTaskPayload,
    GetPlainResultsPaylaod,
)
from search.logic.execute_search import run_search_task, add_items_from_active_sources
from search.logic.approve_items_and_exit_search import approve_relevant_search_results, exit_search_mode

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

    def thread_function():
        try:
            run_search_task(collection, payload.search_task, request.user.id)  # type: ignore
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

    if len(collection.search_tasks) < 2:
        return HttpResponse(status=400)

    previous_task = SearchTaskSettings(**collection.search_tasks[-2])
    if previous_task.exit_search_mode:
        return HttpResponse(status=400)

    collection.agent_is_running = True
    collection.current_agent_step = "Running search task..."
    collection.search_tasks = collection.search_tasks[:-2]
    collection.save(update_fields=["agent_is_running", "current_agent_step", "search_tasks"])

    def thread_function():
        try:
            run_search_task(collection, previous_task, request.user.id)  # type: ignore
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


@api.post("add_items_from_active_sources")
def add_items_from_active_sources_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    new_items = add_items_from_active_sources(collection, request.user.id, is_new_collection=False)  # type: ignore
    result = {"new_item_count": len(new_items)}

    return HttpResponse(json.dumps(result), status=200, content_type="application/json")


@api.post("exit_search_mode")
def exit_search_mode_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only(
            "created_by", "items_last_changed", "search_sources", "explanation_log"
        ).get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    exit_search_mode(collection, payload.class_name)

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

    approve_relevant_search_results(collection, payload.class_name)

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
