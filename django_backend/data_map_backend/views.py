from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers

from .models import Organization


@csrf_exempt
def get_organizations(request):
    if request.method != 'GET':
        return HttpResponse(status=405)

    all_objects = Organization.objects.all()
    result = serializers.serialize('json', all_objects)

    return HttpResponse(result, status=200, content_type='application/json')
