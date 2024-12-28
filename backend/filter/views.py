from typing import Iterable
import uuid
from threading import Lock

from ninja import NinjaAPI
from django.http import HttpResponse
from django.db.models import Min, Max
from django.db.models.manager import BaseManager

from data_map_backend.models import CollectionItem, DataCollection
from filter.schemas import AddFilterPayload, FilterIdentifierPayload, ValueRangeInput, ValueRangeOutput, ReplaceRangeFilterPayload

api = NinjaAPI(urls_namespace="filter")

# lock for changing the filters
changing_filters_lock = Lock()


@api.post("add_filter")
def add_filter_route(request, payload: AddFilterPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    with changing_filters_lock:
        try:
            collection = DataCollection.objects.get(id=payload.collection_id)
        except DataCollection.DoesNotExist:
            return HttpResponse(status=404)
        if collection.created_by != request.user:
            return HttpResponse(status=401)

        if payload.filter.uid:
            collection.filters = [f for f in collection.filters if f["uid"] != payload.filter.uid]
        else:
            payload.filter.uid = str(uuid.uuid4())

        collection.filters.append(payload.filter.model_dump())
        collection.save(update_fields=["filters"])

    return payload.filter


@api.post("remove_filter")
def remove_filter_route(request, payload: FilterIdentifierPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    with changing_filters_lock:
        try:
            collection = DataCollection.objects.get(id=payload.collection_id)
        except DataCollection.DoesNotExist:
            return HttpResponse(status=404)
        if collection.created_by != request.user:
            return HttpResponse(status=401)

        collection.filters = [f for f in collection.filters if f["uid"] != payload.filter_uid]
        collection.save()

    return HttpResponse(None, status=204)


@api.post("get_value_range")
def get_value_range_route(request, payload: ValueRangeInput):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    collection_items: BaseManager[CollectionItem] = collection.items.all()  # type: ignore
    values = collection_items.values_list(f'metadata__{payload.field_name}')
    values = [v for v, in values if v is not None]
    min_value = min(values) if values else 0
    max_value = max(values) if values else 1
    result = ValueRangeOutput(min=min_value, max=max_value)
    return result
