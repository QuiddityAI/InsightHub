import json
import logging

import requests

from ..utils import DotDict
from ..models import Dataset
from ..data_backend_client import DATA_BACKEND_HOST

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def data_backend_proxy_view(request, sub_path: str):
    checks_for_routes_partially_available_without_log_in = {
        "/data_backend/stored_map/parameters_and_search_results": lambda x: True,  # needs map_id, is ok
        "/data_backend/search_list_result": _check_map_or_search_body,
        "/data_backend/map": _check_map_or_search_body,
        "/data_backend/map/result": lambda x: True,  # needs map_id, is ok
        "/data_backend/map/selection_statistics": lambda x: True,  # needs map_id, is ok
        "/data_backend/map/thumbnail_atlas": lambda x: True,  # needs thumbnail file name, is ok
        "/data_backend/document/details_by_id": _check_details_by_id,
        "/data_backend/document/export": _check_details_by_id,
        "/data_backend/remote_db_access": _check_remote_db_access,
    }
    checks_for_routes_always_needing_authentication = {
        "/data_backend/classifier/retrain": lambda x: True,  # TODO, but not very harmful
        "/data_backend/classifier/retraining_status": lambda x: True,  # TODO, but not very harmful
        "/data_backend/upload_files": lambda x: True,  # TODO, but not very harmful
        "/data_backend/map/store": lambda x: True,  # TODO, but not very harmful
        "/data_backend/download_file": _check_download_request,
        "/data_backend/upload_files/status": lambda x: True,  # TODO, but not very harmful
    }
    path = request.path
    if path.startswith("/data_backend/download_file"):
        path = "/data_backend/download_file"

    if path not in checks_for_routes_partially_available_without_log_in \
        and path not in checks_for_routes_always_needing_authentication:
        logging.error(f"Unexpected route: {path}")
        return HttpResponse(status=404)

    if path in checks_for_routes_partially_available_without_log_in and \
        not checks_for_routes_partially_available_without_log_in[path](request):
        return HttpResponse(status=401)
    if path in checks_for_routes_always_needing_authentication and \
        (not request.user.is_authenticated or \
        not checks_for_routes_always_needing_authentication[path](request)):
        return HttpResponse(status=401)

    # forward the request to the data backend
    url = DATA_BACKEND_HOST + request.get_full_path()
    response = requests.request(request.method, url, data=request.body, headers=request.headers)

    return HttpResponse(response.content, status=response.status_code, content_type=response.headers.get("Content-Type"))


def _check_map_or_search_body(request):
    params = DotDict(json.loads(request.body))
    for dataset_id in params.search.dataset_ids:
        dataset = Dataset.objects.get(id=dataset_id)
        if not dataset.is_public and request.user not in dataset.organization.members.all():
            return False
    return True


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


def _check_remote_db_access(request):
    params = DotDict(json.loads(request.body))
    dataset = Dataset.objects.get(id=params.dataset_id)
    access_token = params.access_token
    assert isinstance(dataset.defaults, dict)
    if access_token not in dataset.defaults.get('access_tokens', {}):
        return False
    return True
