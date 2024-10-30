import logging
import json

from ninja import NinjaAPI
from django.http import HttpResponse

from data_map_backend.models import CollectionColumn, CollectionItem, DataCollection
from data_map_backend.utils import is_from_backend
from data_map_backend.serializers import CollectionSerializer, CollectionColumnSerializer
from columns.schemas import ColumnCellRange, ColumnConfig, CellDataPayload, ColumnIdentifier
from columns.logic.process_column import extract_question_from_collection_class_item_query, remove_column_data_from_collection_items

api = NinjaAPI(urls_namespace="columns")


@api.post("add_column")
def add_column_route(request, payload: ColumnConfig):
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    if not payload.name.strip():
        return HttpResponse(status=400)

    if not payload.identifier:
        identifier = payload.name.replace(" ", "_").lower()
        tries = 0
        while CollectionColumn.objects.filter(collection_id=payload.collection_id, identifier=identifier).exists():
            identifier += "_"
            tries += 1
            if tries > 10:
                logging.error("Could not create unique identifier for collection column.")
                return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=payload.collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    column = CollectionColumn.objects.create(
        collection_id=payload.collection_id,
        name=payload.name,
        identifier=identifier,
        field_type=payload.field_type,
        expression=payload.expression,
        source_fields=payload.source_fields,
        module=payload.module,
        parameters=payload.parameters,
    )

    data = CollectionColumnSerializer(column).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@api.post("delete_column")
def delete_column_route(request, payload: ColumnIdentifier):
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        column = CollectionColumn.objects.select_related("collection").get(id=payload.column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    remove_column_data_from_collection_items(CollectionItem.objects.filter(collection=column.collection), column.identifier)

    column.delete()

    return HttpResponse(None, status=204)


@api.post("set_cell_data")
def set_cell_data_route(request, payload: CellDataPayload):
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        item = CollectionItem.objects.select_related("collection").get(id=payload.collection_item_id)
    except CollectionItem.DoesNotExist:
        return HttpResponse(status=404)
    if item.collection.created_by != request.user:
        return HttpResponse(status=401)

    if not item.column_data:
        item.column_data = {}  # type: ignore

    item.column_data[payload.column_identifier] = payload.cell_data
    item.save()

    return HttpResponse(None, status=204)


@api.post("process_column")
def process_column_route(request, payload: ColumnCellRange):
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        column = CollectionColumn.objects.select_related("collection").get(id=payload.column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    if not column.module or column.module == "notes":
        pass
    else:
        extract_question_from_collection_class_item_query(column.collection, payload.class_name, column, payload.offset, payload.limit, payload.order_by, payload.collection_item_id, request.user.id)

    data = CollectionSerializer(column.collection).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@api.post("remove_column_data")
def remove_column_data_route(request, payload: ColumnCellRange):
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        column = CollectionColumn.objects.select_related("collection").get(id=payload.column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    # remove data from collection items:
    collection_items = CollectionItem.objects.filter(collection=column.collection, classes__contains=[payload.class_name])
    collection_items = collection_items.order_by(payload.order_by)
    collection_items = collection_items[payload.offset:payload.offset+payload.limit] if payload.limit > 0 else collection_items[payload.offset:]
    remove_column_data_from_collection_items(collection_items, column.identifier)

    return HttpResponse(None, status=204)

