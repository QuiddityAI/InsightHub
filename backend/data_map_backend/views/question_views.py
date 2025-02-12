import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from data_map_backend.models import ServiceUsage

from .other_views import is_from_backend


@csrf_exempt
def track_service_usage(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        service_name: str = data["service_name"]
        amount: int = data["amount"]
        cause: str = data["cause"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    usage_tracker = ServiceUsage.get_usage_tracker(user_id, service_name)
    result = usage_tracker.track_usage(amount, cause)

    return HttpResponse(json.dumps(result), content_type="application/json", status=200)


@csrf_exempt
def get_service_usage(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)
    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        service_name: str = data["service_name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    usage_tracker = ServiceUsage.get_usage_tracker(user_id, service_name)
    result = {
        "usage_current_period": usage_tracker.get_current_period().usage,
        "limit_per_period": usage_tracker.limit_per_period,
        "period_type": usage_tracker.period_type,
    }

    return HttpResponse(json.dumps(result), content_type="application/json", status=200)
