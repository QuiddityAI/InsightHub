import json
import threading

from django.http import HttpResponse

from ninja import NinjaAPI, Schema

from data_map_backend.models import DataCollection
from data_map_backend.schemas import CollectionIdentifier

from search.schemas import RunSearchTaskPayload
from search.logic import run_search_task, add_items_from_active_sources, exit_search_mode, approve_relevant_search_results

api = NinjaAPI(urls_namespace="search")


@api.post("run_search_task")
def run_search_task_route(request, payload: RunSearchTaskPayload):
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
    collection.save()

    def thread_function():
        try:
            run_search_task(collection, payload.search_task, request.user.id)
        finally:
            collection.agent_is_running = False
            collection.current_agent_step = None
            collection.save()

    threading.Thread(target=thread_function).start()

    return HttpResponse(None, status=204, content_type="application/json")


@api.post("add_items_from_active_sources")
def add_items_from_active_sources_route(request, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    new_item_count = add_items_from_active_sources(collection, request.user.id, is_new_collection=False)
    result = {"new_item_count": new_item_count}

    return HttpResponse(json.dumps(result), status=200, content_type="application/json")


@api.post("exit_search_mode")
def exit_search_mode_route(request, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    exit_search_mode(collection, payload.class_name)

    return HttpResponse(None, status=204, content_type="application/json")


@api.post("approve_relevant_search_results")
def approve_relevant_search_results_route(request, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    approve_relevant_search_results(collection, payload.class_name)

    return HttpResponse(None, status=204, content_type="application/json")
