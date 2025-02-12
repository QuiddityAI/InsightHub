import json
import logging
import os

import requests
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from data_map_backend.models import DataCollection, Dataset
from data_map_backend.utils import DotDict

BACKEND_AUTHENTICATION_SECRET = os.getenv("BACKEND_AUTHENTICATION_SECRET", "not_set")
DATA_BACKEND_HOST = os.getenv("data_backend_host", "http://localhost:55123")


@csrf_exempt
def data_backend_proxy_view(request, sub_path: str):
    checks_for_routes_partially_available_without_log_in = {
        "/data_backend/map/thumbnail_atlas": lambda x: True,  # needs thumbnail file name, is ok
        "/data_backend/document/details_by_id": _check_details_by_id,
        "/data_backend/document/export": _check_details_by_id,
        "/data_backend/collection/export": _check_collection_export,
        "/data_backend/collection/table/export": _check_collection_export,
        "/data_backend/remote_db_access": _check_remote_db_access,
        "/data_backend/local_image": lambda x: True,  # TODO, but not very harmful, need to know file name
        "/data_backend/remove_items": _check_if_from_backend,
        "/data_backend/dataset": _check_if_from_backend,
        "/data_backend/update_database_layout": _check_if_from_backend,
        "/data_backend/health": _check_if_from_backend,
        "/data_backend/db_health": _check_if_from_backend,
        "/data_backend/insert_many_sync": lambda x: True,  # TODO
    }
    checks_for_routes_always_needing_authentication = {
        "/data_backend/classifier/retrain": lambda x: True,  # TODO, but not very harmful
        "/data_backend/classifier/retraining_status": lambda x: True,  # TODO, but not very harmful
        "/data_backend/map/store": lambda x: True,  # TODO, but not very harmful
        "/data_backend/download_file": _check_download_request,
        "/data_backend/upload_files/status": lambda x: True,  # TODO, but not very harmful
        "/data_backend/import_forms": lambda x: True,  # TODO, but not very harmful
    }
    path = request.path
    if path.startswith("/data_backend/download_file"):
        path = "/data_backend/download_file"
    elif path.startswith("/data_backend/local_image"):
        path = "/data_backend/local_image"
    elif path.startswith("/data_backend/map/thumbnail_atlas"):
        path = "/data_backend/map/thumbnail_atlas"
    elif path.startswith("/data_backend/dataset/"):
        path = "/data_backend/dataset"

    if (
        path not in checks_for_routes_partially_available_without_log_in
        and path not in checks_for_routes_always_needing_authentication
    ):
        logging.error(f"Unexpected route: {path}")
        return HttpResponse(status=404)

    if (
        path in checks_for_routes_partially_available_without_log_in
        and not checks_for_routes_partially_available_without_log_in[path](request)
    ):
        return HttpResponse(status=401)
    if path in checks_for_routes_always_needing_authentication and (
        not request.user.is_authenticated or not checks_for_routes_always_needing_authentication[path](request)
    ):
        return HttpResponse(status=401)

    # forward the request to the data backend
    full_path = request.get_full_path().replace("/data_backend/", "/legacy_backend/")
    url = DATA_BACKEND_HOST + full_path
    response = requests.request(request.method, url, data=request.body, headers=request.headers)

    return HttpResponse(
        response.content, status=response.status_code, content_type=response.headers.get("Content-Type")
    )


def _check_download_request(request):
    try:
        dataset_id = int(request.path.split("/")[3])
        dataset = Dataset.objects.get(id=dataset_id)
        if not dataset.is_public and request.user not in dataset.organization.members.all():
            return False
    except Exception as e:
        logging.error(f"Error in _check_download_request: {e}")
        return False
    return True


def _check_details_by_id(request):
    params = DotDict(json.loads(request.body))
    # TODO: this might be a performance bottleneck if many items need to be retrieved
    dataset = Dataset.objects.get(id=params.dataset_id)
    if not dataset.is_public and request.user not in dataset.organization.members.all():
        return False
    return True


def _check_collection_export(request):
    params = DotDict(json.loads(request.body))
    collection = DataCollection.objects.get(id=params.collection_id)
    if not collection.is_public and request.user != collection.created_by:
        return False
    return True


def _check_remote_db_access(request):
    params = DotDict(json.loads(request.body))
    dataset = Dataset.objects.get(id=params.dataset_id)
    access_token = params.access_token
    assert isinstance(dataset.merged_advanced_options, dict)
    if access_token not in dataset.merged_advanced_options.get("access_tokens", {}):
        return False
    return True


def _check_if_from_backend(request):
    return request.META.get("HTTP_AUTHORIZATION") == f"{BACKEND_AUTHENTICATION_SECRET}"
