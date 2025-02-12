import json
import logging
import os

import cbor2
from django.http import FileResponse, HttpResponse
from django.http.response import HttpResponseBase
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from data_map_backend.utils import DotDict
from ingest.logic.common import UPLOADED_FILES_FOLDER
from ingest.logic.upload_files import get_upload_task_status, upload_files_or_forms

from .database_client.django_client import get_or_create_default_dataset
from .database_client.forward_local_db import forward_local_db
from .database_client.text_search_engine_client import TextSearchEngineClient
from .database_client.vector_search_engine_client import VectorSearchEngineClient
from .logic.export_converters import (
    export_collection,
    export_collection_table,
    export_item,
)
from .logic.insert_logic import insert_many, insert_vectors, update_database_layout
from .logic.search_common import get_document_details_by_id

# --- New Routes: ---

# search needs:
#   input: text, image, document (if generator in same embd space avail.)
#   input: negative query (text, image, document) or direction e.g. for image as a word
#   where: vector fields (threshold algorithm (knee)), text fields (fix typo, synonyms etc.)
#   enrich results (only for map?, with neural search per text result etc.)
#   filter results (remove if not both vectors are similar to query etc.)
#   re-score algorithm (tokenizer, aggregation or generator)
#   near-duplicate removal or grouping
#   - How to handle negative queries?
# list only: rank fusion (based on new score, or alternating),
#   highlighting (tokenizer) (on-demand for map, means tf-idf corpus should be kept)
# long list search: updated with map features
# map needs:
#   input: existing vector or set of text fields for w2v
#   multiply with direction word (generator, w2v)
#   umap / t-SNE
#   hdbscan / custom clusterizer
#   cluster title (tf-idf, generative ai)
#   visual settings (color, size, etc.)

# user settings: fields to search, enrich?, map field(s), cluster size

# How to make it customizable and still offer default search and map for datasets?
# -> as currently, offer all settings in UI and select basic defaults based on dataset
# How to apply search and map settings to different datasets (with different field names etc.)?
# Dataset could have default set of vector and text search / map fields, but
# what if there should be two search / map settings for the same dataset?
# E.g. for products, search in title only or in reviews, map based on image or on reviews
# Should search and map settings be separated? Would map always use same search settings as list?
# map might be enriched much more, clustering might be done on different aspect (only image, not title)
# given 100 products all called "white t-shirt", search by title but map by image


URLS = []


def convert_flask_to_django_route(path_pattern, methods=["GET"]):
    path_pattern = path_pattern.lstrip("/")
    path_pattern = path_pattern.replace("data_backend/", "")

    def decorator(original_route):
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return HttpResponse(status=405)
            request.json = (
                json.loads(request.body)
                if request.body and request.headers.get("Content-Type") == "application/json"
                else {}
            )
            request.args = request.GET
            request.form = request.POST
            result = original_route(request, *args, **kwargs)
            if isinstance(result, tuple) and len(result) == 2:
                data, status_code = result
            else:
                data = result
                status_code = 200
            if isinstance(data, HttpResponseBase):
                return data
            if isinstance(data, str):
                content_type = None
            else:
                data = json.dumps(data)
                content_type = "application/json"
            return HttpResponse(data, status=status_code, content_type=content_type)

        URLS.append(path(path_pattern, wrapper))
        return wrapper

    return decorator


def jsonify(data, status_code=200):
    data = json.dumps(data)
    return HttpResponse(data, status=status_code, content_type="application/json")


def send_from_directory(directory, filename):
    full_path = os.path.join(directory, filename)

    if not os.path.realpath(full_path).startswith(os.path.realpath(directory)):
        return "file not found", 404

    if not os.path.exists(full_path):
        return "file not found", 404

    return FileResponse(open(full_path, "rb"))


@convert_flask_to_django_route("/data_backend/update_database_layout", methods=["POST"])
def update_database_layout_route(
    request,
):
    # TODO: check auth
    params = DotDict(request.json)  # type: ignore
    try:
        update_database_layout(params.dataset_id)
    except Exception as e:
        logging.warning("Error updating database layout", exc_info=True)
        return repr(e), 500
    return "", 204


@convert_flask_to_django_route("/data_backend/insert_many_sync", methods=["POST"])
def insert_many_sync_route(
    request,
):
    # TODO: check auth
    params = DotDict(request.json)  # type: ignore
    try:
        insert_many(params.dataset_id, params.elements, params.skip_generators)
    except Exception as e:
        logging.warning("Error inserting many items", exc_info=True)
        return repr(e), 500
    return "", 204


@convert_flask_to_django_route("/data_backend/insert_vectors_sync", methods=["POST"])
def insert_vectors_sync_route(
    request,
):
    # TODO: check auth
    params = DotDict(cbor2.loads(request.data))  # type: ignore
    try:
        insert_vectors(
            params.dataset_id, params.vector_field, params.item_pks, params.vectors, params.excluded_filter_fields
        )
    except Exception as e:
        logging.warning("Error inserting many items", exc_info=True)
        return repr(e), 500
    return "", 204


@convert_flask_to_django_route("/data_backend/import_forms", methods=["POST"])
def import_forms_endpoint(
    request,
):
    """Import items directly from JSON data.
    (No file upload, no extraction, no OCR, but converting, e.g. for URLs)"""
    try:
        params = request.json or {}
        dataset_id: int = params["dataset_id"]
        schema_identifier: str = params["schema_identifier"]
        user_id: int = params["user_id"]
        organization_id: int = params["organization_id"]
        import_converter: str = params["import_converter"]
        collection_id: int | None = params.get("collection_id")
        collection_class: str | None = params.get("collection_class")
        items: list[dict] = params["items"]
    except KeyError as e:
        return f"parameter missing: {e}", 400
    if dataset_id == -1:
        dataset_id = get_or_create_default_dataset(user_id, schema_identifier, organization_id).id
    task_id = upload_files_or_forms(
        dataset_id, import_converter, None, items, collection_id, collection_class, user_id
    )
    return jsonify({"task_id": task_id, "dataset_id": dataset_id}), 200


@convert_flask_to_django_route("/data_backend/upload_files/status", methods=["POST"])
def upload_files_status_endpoint(
    request,
):
    try:
        params = request.json or {}
        dataset_id: int = params["dataset_id"]
    except KeyError as e:
        return f"parameter missing: {e}", 400
    status = get_upload_task_status(dataset_id)
    return jsonify(status)


@convert_flask_to_django_route("/data_backend/local_image/<path:image_path>", methods=["GET"])
def retrieve_local_image(request, image_path):
    # FIXME: this is just a hacky way to make Kaggle Fashion images stored in /data work
    image_path = "/" + image_path
    if image_path is None or not os.path.exists(image_path):
        return "image not found", 404

    return send_from_directory("/data", image_path.replace("/data/", ""))


@convert_flask_to_django_route("/data_backend/download_file/<path:file_path>", methods=["GET"])
def download_file(request, file_path):
    path = f"{UPLOADED_FILES_FOLDER}/{file_path}"
    if not os.path.exists(path):
        return "file not found", 404

    return send_from_directory(UPLOADED_FILES_FOLDER, file_path)


@convert_flask_to_django_route("/data_backend/document/details_by_id", methods=["POST"])
def retrieve_document_details_by_id(
    request,
):
    params = request.json or {}
    dataset_id = params.get("dataset_id")
    item_id = params.get("item_id")
    fields: list[str] = params.get("fields")  # type: ignore
    relevant_parts = params.get("relevant_parts")
    get_text_search_highlights = params.get("get_text_search_highlights", False)
    top_n_full_text_chunks = params.get("top_n_full_text_chunks")
    query = params.get("query")
    include_related_collection_items: bool = params.get("include_related_collection_items", False)
    if not all([dataset_id is not None, item_id is not None, fields is not None]):
        return "a parameter is missing", 400
    assert isinstance(fields, list)
    assert dataset_id is not None
    assert item_id is not None

    if relevant_parts:
        # need to convert to json string to make it hashable for caching
        relevant_parts = json.dumps(relevant_parts)
    else:
        relevant_parts = None
    result = get_document_details_by_id(
        dataset_id,
        item_id,
        tuple(fields),
        relevant_parts,  # type: ignore
        top_n_full_text_chunks=top_n_full_text_chunks,
        get_text_search_highlights=get_text_search_highlights,
        query=query,
        include_related_collection_items=include_related_collection_items,
    )

    if result is None:
        return "document not found", 404

    return result


@convert_flask_to_django_route("/data_backend/document/export", methods=["POST"])
def export_document_route(
    request,
):
    params = request.json or {}
    params = DotDict(params)
    exported_data = export_item(params.dataset_id, params.item_id, params.converter_identifier)

    return exported_data


@convert_flask_to_django_route("/data_backend/collection/export", methods=["POST"])
def export_collection_route(
    request,
):
    params = request.json or {}
    params = DotDict(params)
    exported_data = export_collection(params.collection_id, params.class_name, params.converter_identifier)

    return exported_data


@convert_flask_to_django_route("/data_backend/collection/table/export", methods=["POST"])
def export_collection_table_route(
    request,
):
    params = request.json or {}
    params = DotDict(params)
    exported_data = export_collection_table(
        params.collection_id, params.class_name, params.converter_identifier, params.format_identifier
    )

    return exported_data


# -------------------- Remote DB Access --------------------


@convert_flask_to_django_route("/data_backend/remote_db_access", methods=["POST"])
def remote_db_access_route(
    request,
):
    # permissions were already checked in the organization backend
    params = request.json or {}
    params = DotDict(params)
    result = forward_local_db(params)
    return jsonify({"result": result})
