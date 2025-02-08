import json
import logging
import threading
import time

from django.http import HttpRequest, HttpResponse
from llmonkey.llms import BaseLLMModel
from ninja import NinjaAPI
import dspy
from columns.logic.process_column import (
    get_collection_items_from_cell_range,
    process_cells_blocking,
    remove_column_data_from_collection_items,
)
from columns.schemas import (
    CellDataPayload,
    ColumnCellRange,
    ColumnConfig,
    ColumnIdentifier,
    ProcessColumnPayload,
    UpdateColumnConfig,
)
from data_map_backend.models import CollectionColumn, CollectionItem, DataCollection
from data_map_backend.notifier import default_notifier
from data_map_backend.serializers import (
    CollectionColumnSerializer,
    CollectionSerializer,
)
from config.utils import get_default_dspy_llm


class TitleSignature(dspy.Signature):
    """Given the user question or task, provide a short title that best describes the results of this question or task.
    Title should consist of 1-3 words.
    """

    user_question: str = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired output language for the title")
    title: str = dspy.OutputField()


title_predictor = dspy.Predict(TitleSignature)


class ColumnLanguageSignature(dspy.Signature):
    """Given the user question or task and the title, provide the language code of this question or task.
    Output language code should be a two-letter code.
    """

    user_question: str = dspy.InputField()
    language_code: str = dspy.OutputField()


column_language_predictor = dspy.Predict(ColumnLanguageSignature)

api = NinjaAPI(urls_namespace="columns")


@api.post("add_column")
def add_column_route(request: HttpRequest, payload: ColumnConfig):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    default_notifier.info(f"Column added: '{payload.expression}'", request.user)

    payload.name = payload.name.strip() if payload.name else None
    payload.expression = payload.expression.strip() if payload.expression else None
    if payload.module in ["llm", "relevance"] and not (payload.name or payload.expression):
        return HttpResponse(status=400)

    if payload.module in ["llm", "relevance"] and not payload.parameters.get("language"):
        model = get_default_dspy_llm("column_language")
        with dspy.context(lm=dspy.LM(**model.to_litellm())):
            lang = column_language_predictor(user_question=payload.expression).language_code
        payload.parameters["language"] = lang
    else:
        lang = payload.parameters.get("language")

    if not payload.name:
        if payload.module == "llm":
            if not payload.expression:
                logging.error("No expression provided for LLM column.")
                return HttpResponse(status=400)
            try:
                model = get_default_dspy_llm("column_title")
                with dspy.context(lm=dspy.LM(**model.to_litellm())):
                    payload.name = title_predictor(user_question=payload.expression, target_language=lang).title
            except Exception as e:
                payload.name = "Column"
        else:
            module_name_map = {
                "relevance": "Relevance",
                "web_search": "Web Search",
                "item_field": payload.source_fields[0],
                "notes": "Notes",
                "website_scraping": "Website Text",
                "email": "E-Mail",
            }
            payload.name = module_name_map.get(payload.module, "Column")
    if not payload.name:
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
        collection = DataCollection.objects.only("created_by").get(id=payload.collection_id)
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
        parameters=payload.parameters,
    )

    data = CollectionColumnSerializer(column).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@api.post("update_column")
def update_column_route(request: HttpRequest, payload: UpdateColumnConfig):
    if not request.user.is_authenticated:
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
def delete_column_route(request: HttpRequest, payload: ColumnIdentifier):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        column = CollectionColumn.objects.select_related("collection").get(id=payload.column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    remove_column_data_from_collection_items(
        CollectionItem.objects.filter(collection=column.collection), column.identifier
    )

    column.delete()

    return HttpResponse(status=204)


@api.post("set_cell_data")
def set_cell_data_route(request: HttpRequest, payload: CellDataPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        item = CollectionItem.objects.select_related("collection").get(id=payload.collection_item_id)
    except CollectionItem.DoesNotExist:
        return HttpResponse(status=404)
    if item.collection.created_by != request.user:
        return HttpResponse(status=401)

    if not item.column_data:
        item.column_data = {}

    item.column_data[payload.column_identifier] = payload.cell_data
    item.save(update_fields=["column_data"])

    return HttpResponse(status=204)


@api.post("process_column")
def process_column_route(request: HttpRequest, payload: ProcessColumnPayload):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        column = CollectionColumn.objects.select_related("collection").get(id=payload.cell_range.column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    if not column.module or column.module == "notes":
        pass
    else:
        collection_items = get_collection_items_from_cell_range(column, payload.cell_range)
        if payload.remove_content:
            remove_column_data_from_collection_items(collection_items, column.identifier)

        def in_thread():
            process_cells_blocking(collection_items, column, column.collection, request.user.id)  # type: ignore

        thread = threading.Thread(target=in_thread)
        thread.start()
        # wait till at least columns_with_running_processes is set:
        time.sleep(0.1)

    data = CollectionSerializer(column.collection).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@api.post("remove_column_data")
def remove_column_data_route(request: HttpRequest, payload: ColumnCellRange):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        column = CollectionColumn.objects.select_related("collection").get(id=payload.column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    collection_items = get_collection_items_from_cell_range(column, payload)
    remove_column_data_from_collection_items(collection_items, column.identifier)

    return HttpResponse(status=204)


@api.get("available_llm_models")
def get_available_llm_models_route(request):
    config_dict = BaseLLMModel.available_model_configs()
    required_capability = "chat"
    configs = []
    for model_id, config in config_dict.items():  # type: ignore
        config["model_id"] = model_id
        if config["location"] != "EU":
            config["verbose_name"] += f" (non-EU)"
        if required_capability in config["capabilities"]:
            configs.append(config)
    return configs
