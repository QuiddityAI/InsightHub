import logging
import time

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI

from data_map_backend.models import DataCollection
from data_map_backend.schemas import CollectionIdentifier
from map.logic.map_generation_pipeline import generate_new_map
from map.schemas import (
    MapData,
    MapMetadata,
    NewMapPayload,
    ProjectionsEndpointResponse,
    RemoveCollectionItemsPayload,
    RemoveCollectionItemsResponse,
)

api = NinjaAPI(urls_namespace="map")


@api.post("get_new_map")
def get_new_map_route(request: HttpRequest, payload: NewMapPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    projections = generate_new_map(collection, payload.parameters)
    if isinstance(projections, str):
        # there was an error
        logging.error(projections)
        collection.map_metadata = {}
        collection.map_data = {}
        collection.save()
        return HttpResponse(status=204)
    result = ProjectionsEndpointResponse(projections=projections, metadata=collection.map_metadata)
    return result.dict()


@api.post("get_existing_projections")
def get_existing_projections_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only("created_by", "map_data", "map_metadata").get(
            id=payload.collection_id
        )
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    if not collection.map_data:
        return None
    map_data = MapData(**collection.map_data)
    result = ProjectionsEndpointResponse(projections=map_data.projections, metadata=collection.map_metadata)
    return result.dict()


@api.post("get_cluster_info")
def get_cluster_info_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only("created_by", "map_metadata").get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    timeout = 60
    start = time.time()
    map_metadata = MapMetadata(**collection.map_metadata) if collection.map_metadata else None
    while not map_metadata or not map_metadata.clusters_are_ready:
        time.sleep(0.1)
        if (time.time() - start) > timeout:
            return HttpResponse(status=500)
        collection.refresh_from_db(fields=["map_metadata"])
        map_metadata = MapMetadata(**collection.map_metadata) if collection.map_metadata else None

    collection.refresh_from_db(fields=["map_data"])
    map_data = MapData(**collection.map_data)
    return map_data.clusters_by_id


@api.post("get_thumbnail_data")
def get_thumbnail_data_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only("created_by", "map_metadata").get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    timeout = 60
    start = time.time()
    map_metadata = MapMetadata(**collection.map_metadata) if collection.map_metadata else None
    while not map_metadata or not map_metadata.clusters_are_ready:
        time.sleep(0.1)
        if (time.time() - start) > timeout:
            return HttpResponse(status=500)
        collection.refresh_from_db(fields=["map_metadata"])
        map_metadata = MapMetadata(**collection.map_metadata) if collection.map_metadata else None

    collection.refresh_from_db(fields=["map_data"])
    map_data = MapData(**collection.map_data)
    return map_data.thumbnail_data


# TODO: this should be moved to a separate collection_items Django app


@api.post("remove_collection_items")
def remove_collection_items_route(request: HttpRequest, payload: RemoveCollectionItemsPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.only("created_by").get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    collection_items = collection.items.filter(id__in=payload.item_ids)
    removed_item_ids = list(collection_items.values_list("id", flat=True))
    collection_items.delete()

    result = RemoveCollectionItemsResponse(
        removed_item_ids=removed_item_ids, updated_count_per_class=collection.actual_classes
    )

    return result
