import json

from django.http import HttpResponse, HttpRequest

from ninja import NinjaAPI

from data_map_backend.models import DataCollection, User
from data_map_backend.serializers import CollectionSerializer
from data_map_backend.schemas import CollectionIdentifier
from .schemas import CreateCollectionSettings
from .logic import create_collection_using_mode

api = NinjaAPI(urls_namespace="workflows")


@api.post("create_collection")
def create_collection(request: HttpRequest, payload: CreateCollectionSettings):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    assert isinstance(request.user, User)
    item = create_collection_using_mode(request.user, payload)

    dataset_dict = CollectionSerializer(instance=item).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type="application/json")


@api.post("cancel_agent")
def cancel_agent_route(request: HttpRequest, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        item = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    item.cancel_agent_flag = True
    item.save(update_fields=["cancel_agent_flag"])

    return HttpResponse(None, status=204)
