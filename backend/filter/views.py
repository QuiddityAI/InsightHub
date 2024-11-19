import uuid

from ninja import NinjaAPI
from django.http import HttpResponse

from data_map_backend.models import DataCollection
from filter.schemas import AddFilterPayload, FilterIdentifierPayload

api = NinjaAPI(urls_namespace="filter")


@api.post("add_filter")
def add_filter(request, payload: AddFilterPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    if not payload.filter.uid:
        payload.filter.uid = str(uuid.uuid4())

    collection.filters.append(payload.filter.model_dump())
    collection.save()

    return payload.filter


@api.post("remove_filter")
def remove_filter(request, payload: FilterIdentifierPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    collection.filters = [f for f in collection.filters if f["uid"] != payload.filter_uid]
    collection.save()

    return HttpResponse(None, status=204)
