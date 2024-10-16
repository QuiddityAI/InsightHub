import time

from django.http import HttpResponse
from ninja import NinjaAPI

from data_map_backend.models import DataCollection
from data_map_backend.schemas import CollectionIdentifier

from .schemas import NewMapPayload, MapData
from .logic import generate_new_map

api = NinjaAPI(urls_namespace="map")


@api.post("get_new_map")
def get_new_map_route(request, payload: NewMapPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    projections = generate_new_map(collection, payload.parameters)
    if isinstance(projections, str):
        collection.map_data = None
        collection.save()
        return HttpResponse(status=500)
    return projections


@api.post("get_existing_projections")
def get_existing_projections_route(request, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    map_data = MapData(**collection.map_data)
    return map_data.projections


@api.post("get_cluster_info")
def get_cluster_info_route(request, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    timeout = 60
    start = time.time()
    map_data = MapData(**collection.map_data)
    while not map_data.clusters_are_ready:
        time.sleep(0.1)
        collection.refresh_from_db()
        map_data = MapData(**collection.map_data)
        if (time.time() - start) > timeout:
            return HttpResponse(status=500)

    return map_data.clusters_by_id


@api.post("get_thumbnail_data")
def get_thumbnail_data_route(request, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    timeout = 60
    start = time.time()
    map_data = MapData(**collection.map_data)
    while not map_data.thumbnails_are_ready:
        time.sleep(0.1)
        collection.refresh_from_db()
        map_data = MapData(**collection.map_data)
        if (time.time() - start) > timeout:
            return HttpResponse(status=500)

    return map_data.thumbnail_data
