import json
import logging
import os
from typing import Optional

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone

from ninja import NinjaAPI

from data_map_backend.models import DataCollection
from data_map_backend.serializers import CollectionSerializer
from data_map_backend.utils import is_from_backend
from .schemas import CreateCollectionSettings
from .logic import create_collection_using_mode

api = NinjaAPI()


@api.post("create_collection")
def create_collection(request, payload: CreateCollectionSettings):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    item = create_collection_using_mode(request.user, payload)

    dataset_dict = CollectionSerializer(instance=item).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type="application/json")
