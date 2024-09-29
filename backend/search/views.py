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

from ninja import NinjaAPI, Schema

from data_map_backend.models import DataCollection, CollectionItem
from data_map_backend.serializers import CollectionSerializer
from data_map_backend.utils import is_from_backend

api = NinjaAPI()


class CollectionIdentifier(Schema):
    collection_id: int
    class_name: str


@api.post("exit_search_mode")
def exit_search_mode(request, payload: CollectionIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    if collection.created_by != request.user:
        return HttpResponse(status=401)

    all_items = CollectionItem.objects.filter(collection_id=payload.collection_id, classes__contains=[payload.class_name])
    candidates = all_items.filter(Q(relevance=0) | Q(relevance=1) | Q(relevance=-1))
    logging.warning(f"Deleting {candidates.count()} items from collection {payload.collection_id} in class {payload.class_name}")
    candidates.delete()
    collection.items_last_changed = timezone.now()
    collection.save()

    return HttpResponse(None, status=204, content_type="application/json")
