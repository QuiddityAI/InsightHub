import datetime
import json
import logging
import time

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone

from .models import DataCollection, CollectionItem, Dataset, Organization, SearchHistoryItem, StoredMap, Generator, TrainedClassifier
from .serializers import CollectionItemSerializer, CollectionSerializer, DatasetSerializer, OrganizationSerializer, SearchHistoryItemSerializer, StoredMapSerializer, GeneratorSerializer, TrainedClassifierSerializer


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"


def is_from_backend(request):
    # FIXME: this is not secure
    possible_hosts = ('http://localhost:55125', 'http://home-server:55125',
                      'http://localhost:55425', 'http://home-server:55425',
                      None)
    return request.META.get('HTTP_ORIGIN') in possible_hosts


@csrf_exempt
def get_health(request):
    return HttpResponse("", status=200)


@csrf_exempt
def get_current_user(request):
    user = request.user
    response_json = json.dumps({
        'id': user.id,
        'logged_in': user.is_authenticated,
        'username': user.username,
        'is_staff': user.is_staff,
    })
    return HttpResponse(response_json, status=200, content_type='application/json')


@csrf_exempt
def get_available_organizations(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = Organization.objects.all()

    result = []
    for item in items:
        if not item.members.filter(id=request.user.id).exists():
            continue
        result.append(item)

    serialized_data = OrganizationSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')

@csrf_exempt
def get_dataset(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        dataset_id: int = data["dataset_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    dataset: Dataset = Dataset.objects.get(id=dataset_id)

    if not dataset.is_public and not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)
    elif not dataset.is_public and not dataset.organization.members.filter(id=request.user.id).exists() and not is_from_backend(request):
        return HttpResponse(status=401)

    dataset_dict = DatasetSerializer(instance=dataset).data
    assert isinstance(dataset_dict, dict)
    dataset_dict["object_fields"] = {item['identifier']: item for item in dataset_dict["object_fields"]}

    result = json.dumps(dataset_dict)
    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_available_datasets(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        organization_id: int = data.get("organization_id")
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    datasets = Dataset.objects.filter(Q(is_template=False))
    # TODO: filter by organization_id later on:
    # datasets = Dataset.objects.filter(Q(organization_id=organization_id))

    result = []
    for dataset in datasets:
        if not dataset.is_public and not request.user.is_authenticated:
            continue
        elif not dataset.is_public and not dataset.organization.members.filter(id=request.user.id).exists():
            continue
        result.append({"id": dataset.id, "name": dataset.name,  # type: ignore
                       "entity_name": dataset.entity_name, "entity_name_plural": dataset.entity_name_plural,
                       "short_description": dataset.short_description,
                       })

    result = json.dumps(result)
    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_dataset_templates(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    datasets = Dataset.objects.filter(Q(is_template=True))

    result = []
    for dataset in datasets:
        if not dataset.is_public and not request.user.is_authenticated:
            continue
        elif not dataset.is_public and not dataset.organization.members.filter(id=request.user.id).exists():
            continue
        result.append({"id": dataset.id, "name": dataset.name,  # type: ignore
                       "entity_name": dataset.entity_name, "entity_name_plural": dataset.entity_name_plural,
                       "short_description": dataset.short_description,
                       })

    result = json.dumps(result)
    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def create_dataset(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        name: str = data["name"]
        organization_id: int = data["organization_id"]
        template_id: int = data["template_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return HttpResponse(status=404)
    if not organization.members.filter(id=request.user.id).exists():
        return HttpResponse(status=401)

    try:
        template = Dataset.objects.get(id=template_id)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)
    if not template.is_template:
        return HttpResponse(status=400)

    dataset = template.create_copy()
    dataset.name = name
    dataset.organization = organization
    dataset.is_template = False
    dataset.origin_template = template  # type: ignore
    dataset.admins.add(request.user)
    dataset.save()

    dataset_dict = DatasetSerializer(instance=dataset).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def add_search_history_item(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
        name: str = data["name"]
        display_name: str = data["display_name"]
        parameters: dict = data["parameters"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    item = SearchHistoryItem()
    item.user_id = request.user.id  # type: ignore
    item.organization_id = organization_id  # type: ignore
    item.name = name
    item.display_name = display_name
    item.parameters = parameters  # type: ignore
    item.save()

    serialized_data = SearchHistoryItemSerializer(instance=item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_search_history(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = SearchHistoryItem.objects.filter(user_id=request.user.id, organization_id=organization_id).order_by('-created_at')[:25:-1]
    serialized_data = SearchHistoryItemSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def add_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        name: str = data["name"]
        related_organization_id: int = data["related_organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    item = DataCollection()
    item.created_by = request.user  # type: ignore
    item.name = name
    item.related_organization_id = related_organization_id  # type: ignore
    item.save()

    dataset_dict = CollectionSerializer(instance=item).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def delete_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)
    item.delete()

    return HttpResponse(None, status=204)


@csrf_exempt
def add_collection_class(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    if item.class_names == None:
        item.class_names = [class_name] # type: ignore
    elif class_name not in item.class_names:
        item.class_names.append(class_name)  # type: ignore
    item.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def delete_collection_class(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    all_items = CollectionItem.objects.filter(collection_id=collection_id)
    for item in all_items:
        if (class_name == "_default" and not item.classes) or class_name in item.classes:  # type: ignore
            item.delete()

    classifiers = TrainedClassifier.objects.filter(collection_id=collection_id, class_name=class_name)
    classifiers.delete()

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    if collection.class_names != None and class_name in collection.class_names:
        collection.class_names.remove(class_name)
    collection.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def get_collections(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        related_organization_id: int = data["related_organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = DataCollection.objects.filter(Q(related_organization_id=related_organization_id) & (Q(created_by=request.user.id) | Q(is_public=True))).order_by('created_at')
    serialized_data = CollectionSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user and not collection.is_public and not is_from_backend(request):
        return HttpResponse(status=401)
    serialized_data = CollectionSerializer(collection).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_trained_classifier(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        embedding_space_id: int = data["embedding_space_id"]
        include_vector: bool = data.get("include_vector", False)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        classifier = TrainedClassifier.objects.get(collection_id=collection_id, class_name=class_name, embedding_space_id=embedding_space_id)
    except TrainedClassifier.DoesNotExist:
        result = json.dumps(None)
        return HttpResponse(result, status=200, content_type='application/json')
    if classifier.collection.created_by != request.user and not classifier.collection.is_public and not is_from_backend(request):
        return HttpResponse(status=401)
    serialized_data = TrainedClassifierSerializer(classifier).data
    assert isinstance(serialized_data, dict)
    if not include_vector and "decision_vector" in serialized_data:
        serialized_data["decision_vector_exists"] = len(serialized_data["decision_vector"]) > 0
        del serialized_data["decision_vector"]
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def set_trained_classifier(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        embedding_space_id: int = data["embedding_space_id"]
        decision_vector = data.get("decision_vector")
        highest_score = data.get("highest_score")
        threshold = data.get("threshold")
        metrics = data.get("metrics")
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        classifier = TrainedClassifier.objects.get(collection_id=collection_id, class_name=class_name, embedding_space_id=embedding_space_id)
    except TrainedClassifier.DoesNotExist:
        classifier = TrainedClassifier(collection_id=collection_id, class_name=class_name, embedding_space_id=embedding_space_id)
    if classifier.collection.created_by != request.user and not is_from_backend(request):
        return HttpResponse(status=401)

    if decision_vector is not None:
        classifier.decision_vector = decision_vector
        classifier.last_retrained_at = timezone.now()
    if highest_score is not None:
        classifier.highest_score = highest_score
    if threshold is not None:
        classifier.threshold = threshold
    if metrics is not None:
        classifier.metrics = metrics
    classifier.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def get_collection_items(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name = data["class_name"]
        field_type = data["type"]
        is_positive = data["is_positive"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    if field_type or is_positive:
        all_items = CollectionItem.objects.filter(collection_id=collection_id, field_type=field_type, is_positive=is_positive).order_by('-date_added')
    else:
        # return all examples
        all_items = CollectionItem.objects.filter(collection_id=collection_id).order_by('-date_added')
    # FIXME: filter by class already above (not sure why it's not done in the query above already)
    items = []
    for item in all_items:
        if (class_name == "_default" and not item.classes) or class_name in item.classes:  # type: ignore
            items.append(item)
    serialized_data = CollectionItemSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def add_item_to_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        is_positive: bool = data["is_positive"]
        class_name: str = data.get("class_name", '_default')
        field_type: str = data["field_type"]
        value: str = data["value"]
        weight: float = data["weight"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user and not is_from_backend(request):
        return HttpResponse(status=401)

    items = CollectionItem.objects.filter(collection_id=collection_id, is_positive=is_positive, field_type=field_type, value=value)
    for item in items:
        if class_name in item.classes:  # type: ignore
            # the item exists already, but the weight might need to be updated:
            item.weight = weight
            item.save()
            return HttpResponse(None, status=204)

    item = CollectionItem()
    item.collection_id = collection_id  # type: ignore
    item.is_positive = is_positive
    item.classes = [class_name]  # type: ignore
    item.field_type = field_type
    item.value = value
    item.weight = weight
    item.save()
    dataset_dict = CollectionItemSerializer(instance=item).data
    serialized_data = json.dumps(dataset_dict)

    collection.items_last_changed[class_name] = timezone.now().isoformat()  # type: ignore
    collection.save()

    return HttpResponse(serialized_data, status=200, content_type='application/json')


@csrf_exempt
def remove_collection_item(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_item_id: int = data["collection_item_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection_item = CollectionItem.objects.get(id=collection_item_id)
    except CollectionItem.DoesNotExist:
        return HttpResponse(status=404)
    if collection_item.collection.created_by != request.user:
        return HttpResponse(status=401)

    for class_name in collection_item.classes:  # type: ignore
        collection_item.collection.items_last_changed[class_name] = timezone.now().isoformat()  # type: ignore
    collection_item.collection.save()

    collection_item.delete()

    return HttpResponse(None, status=204)


@csrf_exempt
def remove_collection_item_by_value(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        value: str = data["value"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    collection_items = CollectionItem.objects.filter(collection_id=collection_id, value=value)
    if not collection_items:
        return HttpResponse(status=404)

    removed_items = []
    for item in collection_items:
        if item.collection.created_by != request.user:
            return HttpResponse(status=401)
        if class_name not in item.classes and not (class_name == '_default' and not item.classes):  # type: ignore
            continue
        item_dict = CollectionItemSerializer(instance=item).data
        removed_items.append(item_dict)
        item.delete()

    serialized_data = json.dumps(removed_items)

    return HttpResponse(serialized_data, status=200, content_type='application/json')


@csrf_exempt
def add_stored_map(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        organization_id: int = data["organization_id"]
        name: str = data["name"]
        display_name: str = data["display_name"]
        map_id: str = data["map_id"]
        map_data: str = data["map_data"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    item = StoredMap(id=map_id)
    item.user_id = user_id  # call comes from backend, thats why request.user is not valid  # type: ignore
    item.organization_id = organization_id  # type: ignore
    item.name = name
    item.display_name = display_name
    item.map_data = map_data.encode()  # type: ignore  # FIXME: base64 str needs to be decoded
    item.save()

    serialized_data = StoredMapSerializer(instance=item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_stored_maps(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    # TODO: also show public ones
    items = StoredMap.objects.filter(user_id=request.user.id, organization_id=organization_id).order_by('created_at')[:25]
    serialized_data = StoredMapSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_stored_map_data(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        map_id: str = data["map_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)
    try:
        map_item = StoredMap.objects.get(id=map_id)
    except StoredMap.DoesNotExist:
        return HttpResponse(status=404)
    if map_item.user != request.user:  # TODO: also allow public ones
        return HttpResponse(status=401)
    result = map_item.map_data

    return HttpResponse(result, status=200, content_type='application/octet-stream')


@csrf_exempt
def delete_stored_map(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        stored_map_id: int = data["stored_map_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        map = StoredMap.objects.get(id=stored_map_id)
    except StoredMap.DoesNotExist:
        return HttpResponse(status=404)
    if map.user != request.user:
        return HttpResponse(status=401)

    return HttpResponse(None, status=204)


@csrf_exempt
def get_generators(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    items = Generator.objects.all()
    serialized_data = GeneratorSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


"""
def get_generator_function(name, parameters) -> function:
    pass


def get_changed_fields(primary_key_field, batch, dataset):
    # getting internal id from mongo using primary_key_field needs that field to be indexed
    # in Mongo, which it might not be
    primary_keys = []

    for element in batch:
        primary_keys.append(element[primary_key_field])

    current_versions = []  # TODO: mongo.get(dataset=dataset_id, where primary_key_field in primary_key)
    # alternatively: rely on changed_fields parameter (provided by sender, same for all elements)
    # alternatively: rely on only fields being present that changed -> changed_fields = new_element.keys()

    changed_fields_total = []
    for new_element, current_element in zip(batch, current_versions):
        changed_fields = set()
        for field in new_element.keys():
            if new_element[field] != current_element.get(field):
                changed_fields.insert(field)
        changed_fields_total.append(changed_fields)

    return changed_fields_total


def get_index_settings(dataset):
    vector_db_fields = []
    text_db_fields = []
    filtering_fields = []

    for field in dataset.object_fields:
        if field.is_available_for_search and field.field_type == FieldType.VECTOR:
            vector_db_table_name = f'{dataset.id}_{field.identifier}'
            vector_db_fields.append([field.identifier, vector_db_table_name])
        elif field.is_available_for_search and field.field_type == FieldType.TEXT:
            text_db_table_name = f'{dataset.id}_{field.identifier}'
            text_db_fields.append([field.identifier, text_db_table_name])

        if field.is_available_for_filtering:
            filtering_fields.append(field.identifier)

    return DotDict({'vector_db_fields': vector_db_fields, 'text_db_fields': text_db_fields, 'filtering_fields': filtering_fields})


@csrf_exempt
def add_elements(request):

    # basically update() but with changed_fields being all of them


@csrf_exempt
def update_elements(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)

    dataset_id: str = data["dataset_id"]  # TODO: catch error
    dataset: Dataset = get_dataset(dataset_id)

    # TODO: check generate_if_not_exits and skip_generators settings
    pipeline_steps = get_pipeline_steps()

    batch = data["elements"]

    changed_fields_total = get_changed_fields(primary_key_field, batch, dataset)

    for phase in pipeline_steps:
        for pipeline_step in phase:  # TODO: this can be done in parallel
            element_indexes = []
            source_data_total = []

            for i, element in enumerate(batch):
                if not set(changed_fields_total[i]) & set(pipeline_step["source_fields"]): continue
                if pipeline_step.condition_function is not None and not condition(element): continue

                element_indexes.append(i)
                source_data = []
                for source_field in pipeline_step["source_fields"]:
                    source_data.append(element[source_field])
                source_data_total.append(source_data)

            results = pipeline_step.generator_func(source_data_total)

            for element_index, result in zip(element_indexes, results):
                batch[element_index][pipeline_step.target_field] = result
                changed_fields_total[element_index].insert(pipeline_step.target_field)

    for element in batch:
        # make sure primary key exists, if not, generate it
        # TODO: upsert in MongoDB
        pass

    index_settings = get_index_settings(dataset)

    # TODO: ensure the tables exist
    # TODO: skip if no indexed fields

    for element in batch:
        # TODO: if no intersection between db_fields and changed_fields: continue
        filtering_attributes = {}
        for field in index_settings.filtering_fields:
            filtering_attributes[field] = element[field]
        for field, table in index_settings.vector_db_fields:
            # TODO: batch this
            # qdrant.upsert(table: table, id: element.id, vector: element[field], attributes: filtering_attributes)
            pass
        for field, table in index_settings.text_db_fields:
            # TODO: batch this
            # typesense.upsert(table: table, id: element.id, text: element[field], attributes: filtering_attributes)
            pass

    return HttpResponse(status=204, content_type='application/json')


def generate_field_for_existing_elements(dataset_id, field_name, force_recreation):

    # TODO: create Task object for this
    # TODO: get all ids once (to handle that new items may come in during the processing time, but those are handled there)
    # TODO: split up in batches, store current batch number in Task, show progress
    # TODO: do in background thread

    dataset: Dataset = Dataset.objects.get(id=dataset_id)  # TODO: catch error
    # TODO: check if sender is allowed to change data on this dataset / organization
    fields: list[ObjectField] = ObjectField.objects.filter(dataset=dataset_id)
    pipeline_steps = None  # get_pipeline_steps(fields, restrict_to=[field_name])

    all_elements = None  # mongo.get(where dataset_id is dataset_id)

    for step in pipeline_steps:
        # do same as above, but instead of changed_fields for source fields, check if field is empty or force_recreation
        # for element in all_elements: ...
        pass


def get_elements(ids, dataset_id, generate_if_not_exist_fields=[]):
    results = []  # mongo.get(where id in ids)
    dataset: Dataset = Dataset.objects.get(id=dataset_id)  # TODO: catch error
    # TODO: check if sender is allowed to get data from this dataset / organization
    fields: list[ObjectField] = ObjectField.objects.filter(dataset=dataset_id)

    pipeline_steps = None  # get_pipeline_steps(fields, restrict_to=generate_if_not_exist_fields)

    for step in pipeline_steps:
        # do same as above, but instead of changed_fields for source fields, check if field is empty
        # for element in results: ...
        pass

    # commit result to mongo DB and indexes

    return results


def search_by_text_vectorized(dataset_id, field_name, query_text):
    results = []  # mongo.get(where id in ids)
    dataset: Dataset = Dataset.objects.get(id=dataset_id)  # TODO: catch error
    # TODO: check if sender is allowed to get data from this dataset / organization
    field: ObjectField = ObjectField.objects.filter(dataset=dataset_id, name=field_name)

    generator_func = get_generator_function(field.generator.name, field.generator_parameters)
    vector = generator_func([query_text])[0]
    vector_db_table_name = f'{dataset.id}_{field.identifier}'

    # TODO: add filter criteria

    result_ids = None  # qdrant.find_near(vector_db_table_name, vector, limit)

    # add distances to results if not there yet

    objects = None  # mongo.get(where id in ids)
    # this could be slow if abstracts are retrieved, too

    return objects


def get_map_by_text_query_vectorized(dataset_id, field_name, query_text):
    objects = search_by_text_vectorized()

    mapping_vectors = objects[field_name]
    # could be different vectors than search vectors (e.g. search title, but cluster description)

    # add distances of map vectors to query if not there yet

    # UMAP

    # HDBScan

    # cluster titles
    # respect parameter cluster_title_fields (e.g. title + abstract)

    return objects
"""