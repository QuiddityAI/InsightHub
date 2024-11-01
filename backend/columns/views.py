from dataclasses import asdict
import logging
import json
import threading
import time

from ninja import NinjaAPI
from django.http import HttpResponse
from llmonkey.llms import BaseLLMModel, Mistral_Ministral3b

from data_map_backend.models import CollectionColumn, CollectionItem, DataCollection
from data_map_backend.utils import is_from_backend
from data_map_backend.serializers import CollectionSerializer, CollectionColumnSerializer
from columns.schemas import ColumnCellRange, ColumnConfig, CellDataPayload, ColumnIdentifier, UpdateColumnConfig
from columns.logic.process_column import remove_column_data_from_collection_items, get_collection_items_from_cell_range, process_cells_blocking
from columns.logic.column_prompts import column_name_prompt, column_language_prompt

api = NinjaAPI(urls_namespace="columns")


@api.post("add_column")
def add_column_route(request, payload: ColumnConfig):
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    payload.name = payload.name.strip() if payload.name else None
    payload.expression = payload.expression.strip() if payload.expression else None
    if payload.module in ["llm", "relevance"] and not (payload.name or payload.expression):
        return HttpResponse(status=400)

    if not payload.name:
        if payload.module == "llm":
            assert payload.expression
            response = Mistral_Ministral3b().generate_prompt_response(system_prompt=column_name_prompt.replace("{{ expression }}", payload.expression))
            payload.name = response.conversation[-1].content
            payload.name = payload.name.strip().strip('"').strip("'")
            if not payload.name:
                logging.error("Could not generate name for column.")
                return HttpResponse(status=400)
        elif payload.module == "relevance":
            payload.name = "Relevance"
        elif payload.module == "web_search":
            payload.name = "Web Search"
        elif payload.module == "item_field":
            payload.name = payload.source_fields[0]
        elif payload.module == "notes":
            payload.name = "Notes"
        elif payload.module == "website_scraping":
            payload.name = "Website Text"
        elif payload.module == "email":
            payload.name = "E-Mail"
        else:
            payload.name = "Column"
    assert payload.name

    if not payload.identifier:
        identifier = payload.name.replace(" ", "_").lower()
        tries = 0
        while CollectionColumn.objects.filter(collection_id=payload.collection_id, identifier=identifier).exists():
            identifier += "_"
            tries += 1
            if tries > 10:
                logging.error("Could not create unique identifier for collection column.")
                return HttpResponse(status=400)

    if payload.module in ["llm", "relevance"] and not payload.parameters.get("language"):
        prompt = column_language_prompt.replace("{{ expression }}", payload.expression or "").replace("{{ title }}", payload.name)
        response = Mistral_Ministral3b().generate_prompt_response(system_prompt=prompt)
        language = response.conversation[-1].content
        language = language.strip().strip('"').strip("'")
        if len(language) != 2:
            logging.error("Could not generate language for column.")
            language = "en"
        payload.parameters["language"] = language

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
        prompt_template=payload.prompt_template,
        auto_run_for_approved_items=payload.auto_run_for_approved_items,
        auto_run_for_candidates=payload.auto_run_for_candidates,
        determines_relevance=payload.module == "relevance",
        parameters=payload.parameters,
    )

    data = CollectionColumnSerializer(column).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@api.post("update_column")
def update_column_route(request, payload: UpdateColumnConfig):
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        column = CollectionColumn.objects.select_related("collection").get(id=payload.column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    if payload.name:
        column.name = payload.name
    if payload.expression:
        column.expression = payload.expression
    if payload.prompt_template:
        column.prompt_template = payload.prompt_template
    if payload.parameters:
        column.parameters = payload.parameters
    column.auto_run_for_approved_items = payload.auto_run_for_approved_items
    column.auto_run_for_candidates = payload.auto_run_for_candidates

    column.save()

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
        collection_items = get_collection_items_from_cell_range(column, payload)

        def in_thread():
            process_cells_blocking(collection_items, column, column.collection, request.user.id)

        thread = threading.Thread(target=in_thread)
        thread.start()
        # wait till at least columns_with_running_processes is set:
        time.sleep(0.1)

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

    collection_items = get_collection_items_from_cell_range(column, payload)
    remove_column_data_from_collection_items(collection_items, column.identifier)

    return HttpResponse(None, status=204)


@api.get("available_llm_models")
def get_available_llm_models_route(request):
    model_classes = BaseLLMModel.available_models()
    models = {}
    for model_class in model_classes.values():
        config = model_class.config.dict()
        models[model_class.__name__] = {"config": config, "provider": model_class.provider, "identifier": model_class.__name__}
    return models

