from django.http import HttpResponse

from ninja import NinjaAPI

from data_map_backend.models import DataCollection
from data_map_backend.schemas import SetUiSettingsPayload

api = NinjaAPI(urls_namespace="collections")


@api.post("set_ui_settings")
def set_ui_settings_route(request, payload: SetUiSettingsPayload):
    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if request.user != collection.created_by:
        return HttpResponse(status=403)
    collection.ui_settings = payload.ui_settings.model_dump()
    collection.save()
    return HttpResponse(status=200)
