import json
import logging
import operator
import os
from functools import lru_cache, reduce

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models.manager import BaseManager
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from data_map_backend.schemas import ItemRelevance
from data_map_backend.utils import DotDict
from filter.schemas import CollectionFilter
from search.schemas import SearchTaskSettings

from ..models import (
    CollectionItem,
    DataCollection,
    Dataset,
    DatasetSchema,
    ExportConverter,
    FieldType,
    Generator,
    ImportConverter,
    Organization,
    SearchHistoryItem,
    SearchTask,
    ServiceUsage,
    StoredMap,
    TrainedClassifier,
    User,
    generate_unique_database_name,
)
from ..notifier import default_notifier
from ..serializers import (
    CollectionItemSerializer,
    CollectionSerializer,
    DatasetSchemaSerializer,
    DatasetSerializer,
    ExportConverterSerializer,
    GeneratorSerializer,
    ImportConverterSerializer,
    OrganizationSerializer,
    SearchHistoryItemSerializer,
    StoredMapSerializer,
    TrainedClassifierSerializer,
)
from ..utils import is_from_backend


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"


@csrf_exempt
def get_health(request):
    return HttpResponse("", status=200)


@csrf_exempt
def get_current_user(request):
    user = request.user
    if not user.is_authenticated:
        response_json = json.dumps(
            {
                "id": None,
                "logged_in": False,
                "username": None,
                "is_staff": False,
                "used_ai_credits": 0,
                "total_ai_credits": 0,
                "preferences": {},
            }
        )
        return HttpResponse(response_json, status=200, content_type="application/json")
    ai_service_usage = ServiceUsage.get_usage_tracker(user.id, "External AI")
    response_json = json.dumps(
        {
            "id": user.id,
            "logged_in": user.is_authenticated,
            "username": user.username,
            "is_staff": user.is_staff,
            "used_ai_credits": ai_service_usage.get_current_period().usage,
            "total_ai_credits": ai_service_usage.limit_per_period,
            "preferences": user.preferences,
        }
    )
    return HttpResponse(response_json, status=200, content_type="application/json")


@csrf_exempt
def set_user_preferences_route(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        preferences = data["preferences"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    user = request.user
    user.preferences = preferences
    user.save()

    return HttpResponse(status=204)


@csrf_exempt
def get_available_organizations(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    if request.user.is_authenticated:
        organizations = Organization.objects.filter(Q(is_public=True) | Q(members=request.user))
    else:
        organizations = Organization.objects.filter(is_public=True)
    organizations = organizations.distinct().order_by("name")

    # restrict some domains to certain organizations:
    hostname = request.META.get("HTTP_HOST")
    hostnames_that_show_all_orgs = [
        "home-server:55140",
        "feldberg.absclust.com",
        "backend-staging-at:55125",
    ]
    hostnames_that_show_all_orgs += os.environ.get("HOSTNAMES_THAT_SHOW_ALL_ORGANIZATIONS", "").split(",")

    if hostname not in hostnames_that_show_all_orgs and not hostname.startswith(("localhost", "127.0.0.1")):
        organizations = organizations.filter(domains__contains=[hostname])

    serialized_data = OrganizationSerializer(organizations, many=True).data

    # replace list of all datasets of each organization with list of available datasets:
    for organization, serialized in zip(organizations, serialized_data):
        is_member = request.user.is_authenticated and organization.members.filter(id=request.user.id).exists()
        serialized["is_member"] = is_member
        if is_member:
            serialized["datasets"] = [
                dataset.id
                for dataset in Dataset.objects.filter(
                    Q(organization_id=organization.id)
                    & (Q(is_public=True) | Q(is_organization_wide=True) | Q(admins=request.user))
                )
            ]
        else:
            serialized["datasets"] = [
                dataset.id
                for dataset in Dataset.objects.filter(Q(organization_id=organization.id) & Q(is_public=True))
            ]

    result = json.dumps(serialized_data)
    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def get_dataset(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        dataset_id: int = data["dataset_id"]
        additional_fields: tuple = tuple(data.get("additional_fields", []))
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    dataset: Dataset = get_dataset_cached(dataset_id)

    if not is_from_backend(request) and not dataset.is_public:
        is_member = request.user.is_authenticated and dataset.organization.members.filter(id=request.user.id).exists()
        is_admin = request.user.is_authenticated and dataset.admins.filter(id=request.user.id).exists()
        if not ((dataset.is_organization_wide and is_member) or is_admin):
            return HttpResponse(status=401)

    dataset_dict = get_serialized_dataset_cached(dataset_id, additional_fields)

    result = json.dumps(dataset_dict)
    return HttpResponse(result, status=200, content_type="application/json")


@lru_cache(maxsize=128)
def get_dataset_cached(dataset_id: int) -> Dataset:
    return (
        Dataset.objects.select_related(
            "schema",
        )
        .prefetch_related(
            "schema__object_fields",
            "schema__applicable_import_converters",
            "schema__applicable_export_converters",
            "schema__object_fields__generator",
            "schema__object_fields__generator__embedding_space",
            "schema__object_fields__embedding_space",
        )
        .get(id=dataset_id)
    )


@lru_cache(maxsize=128)
def get_serialized_dataset_cached(dataset_id: int, additional_fields: tuple = tuple()) -> DotDict:
    dataset: Dataset = get_dataset_cached(dataset_id)

    dataset_dict = DatasetSerializer(instance=dataset).data
    assert isinstance(dataset_dict, dict)
    dataset_dict["schema"]["object_fields"] = {
        item["identifier"]: item for item in dataset_dict["schema"]["object_fields"]
    }
    if "applicable_export_converters" not in dataset_dict["schema"]:
        dataset_dict["schema"]["applicable_export_converters"] = []
    universal_exporters = ExportConverter.objects.filter(universally_applicable=True)
    serialized_exporters = ExportConverterSerializer(universal_exporters, many=True).data
    dataset_dict["schema"]["applicable_export_converters"].extend(serialized_exporters)
    if "item_count" in additional_fields:
        dataset_dict["item_count"] = dataset.item_count
    return DotDict(dataset_dict)


@csrf_exempt
def get_available_datasets(request):
    # not used currently and outdated (permissions etc.)
    return HttpResponse(status=405)
    # if request.method != 'POST':
    #     return HttpResponse(status=405)

    # try:
    #     data = json.loads(request.body)
    #     organization_id: int = data.get("organization_id")
    # except (KeyError, ValueError):
    #     return HttpResponse(status=400)

    # datasets = Dataset.objects.filter(is_template=False)
    # # TODO: filter by organization_id later on:
    # # datasets = Dataset.objects.filter(Q(organization_id=organization_id))

    # result = []
    # for dataset in datasets:
    #     if not dataset.is_public and not request.user.is_authenticated:
    #         continue
    #     elif not dataset.is_public and not dataset.organization.members.filter(id=request.user.id).exists():
    #         continue
    #     result.append({"id": dataset.id, "name": dataset.name,
    #                    "entity_name": dataset.schema.entity_name, "entity_name_plural": dataset.schema.entity_name_plural,
    #                    "short_description": dataset.schema.short_description,
    #                    })

    # result = json.dumps(result)
    # return HttpResponse(result, status=200, content_type='application/json')


@csrf_exempt
def get_dataset_schemas(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return HttpResponse(status=404)

    if not organization.members.filter(id=request.user.id).exists():
        return HttpResponse(status=401)

    schemas = organization.schemas_for_user_created_datasets.all()

    serialized_data = DatasetSchemaSerializer(schemas, many=True).data

    result = json.dumps(serialized_data)
    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def create_dataset_from_schema(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        name: str = data["name"]
        organization_id: int = data["organization_id"]
        schema_identifier: str = data["schema_identifier"]
        from_ui: bool = data.get("from_ui", False)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    default_notifier.info(f"User {request.user.username} created dataset {name}", user=request.user)

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return HttpResponse(status=404)
    if not organization.members.filter(id=request.user.id).exists():
        return HttpResponse(status=401)
    if not organization.schemas_for_user_created_datasets.filter(identifier=schema_identifier).exists():
        return HttpResponse(status=404)

    try:
        schema = DatasetSchema.objects.get(identifier=schema_identifier)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)

    safe_name = "".join(e for e in name if e.isalnum() or e == "_" or e == " ")
    safe_name = safe_name.replace(" ", "_").lower()

    dataset = Dataset()
    dataset.schema = schema
    dataset.name = name
    dataset.organization = organization
    dataset.created_in_ui = from_ui
    dataset.is_public = False
    dataset.database_name = generate_unique_database_name(f"{request.user.id}_{schema.identifier}_{safe_name}")
    dataset.save()
    dataset.admins.add(request.user)
    dataset.save()

    dataset_dict = DatasetSerializer(instance=dataset).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def get_or_create_default_dataset_route(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        schema_identifier: str = data["schema_identifier"]
        organization_id: int = data["organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    result = get_or_create_default_dataset(user_id, schema_identifier, organization_id)
    if isinstance(result, HttpResponse):
        return result

    dataset = result
    dataset_dict = DatasetSerializer(instance=dataset).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type="application/json")


def get_or_create_default_dataset(
    user_id: int, schema_identifier: str, organization_id: int
) -> Dataset | HttpResponse:
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponse(status=404)

    try:
        organization = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return HttpResponse(status=404)
    if not organization.members.filter(id=user.id).exists():  # type: ignore
        return HttpResponse(status=401)
    if not organization.schemas_for_user_created_datasets.filter(identifier=schema_identifier).exists():
        return HttpResponse(status=404)

    try:
        schema = DatasetSchema.objects.get(identifier=schema_identifier)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)

    default_dataset_name = f"My {schema.name}"
    if Dataset.objects.filter(name=default_dataset_name, organization=organization, admins=user).exists():
        dataset = Dataset.objects.filter(name=default_dataset_name, organization=organization, admins=user).first()
    else:
        dataset = Dataset()
        dataset.schema = schema
        dataset.name = default_dataset_name
        dataset.organization = organization
        dataset.created_in_ui = True
        dataset.is_public = False
        dataset.database_name = generate_unique_database_name(f"{user_id}_my_{schema.identifier}")
        dataset.save()
        dataset.admins.add(user)
        dataset.save()
    assert isinstance(dataset, Dataset)
    return dataset


@csrf_exempt
def change_dataset(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        dataset_id: int = data["dataset_id"]
        updates: dict = data["updates"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)
    if not dataset.admins.filter(id=request.user.id).exists():
        return HttpResponse(status=401)

    allowed_fields = ["name", "short_description", "is_public", "is_organization_wide"]
    for key in updates.keys():
        if key not in allowed_fields:
            return HttpResponse(status=400)

    for key, value in updates.items():
        setattr(dataset, key, value)
    dataset.save()

    dataset_dict = DatasetSerializer(instance=dataset).data
    result = json.dumps(dataset_dict)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def delete_dataset(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        dataset_id: int = data["dataset_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)
    if not dataset.admins.filter(id=request.user.id).exists():
        return HttpResponse(status=401)

    dataset.delete_with_content()

    return HttpResponse(None, status=204)


@csrf_exempt
def get_import_converter(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        identifier: int = data["identifier"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        converter = ImportConverter.objects.get(identifier=identifier)
    except ImportConverter.DoesNotExist:
        return HttpResponse(status=404)

    serialized_data = json.dumps(ImportConverterSerializer(instance=converter).data)
    return HttpResponse(serialized_data, status=200, content_type="application/json")


@csrf_exempt
def get_export_converter(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        identifier: int = data["identifier"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        converter = ExportConverter.objects.get(identifier=identifier)
    except ExportConverter.DoesNotExist:
        return HttpResponse(status=404)

    serialized_data = json.dumps(ExportConverterSerializer(instance=converter).data)
    return HttpResponse(serialized_data, status=200, content_type="application/json")


@csrf_exempt
def add_search_history_item(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    # view is accesible without authentication

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
        name: str = data["name"]
        display_name: str = data["display_name"]
        parameters: dict = data["parameters"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    item = SearchHistoryItem()
    item.user_id = request.user.id if request.user.is_authenticated else None  # type: ignore
    item.organization_id = organization_id  # type: ignore
    item.name = name
    item.display_name = display_name
    item.parameters = parameters
    item.save()
    try:
        user = User.objects.get(id=item.user_id) if item.user_id else None  # type: ignore
        username = user.username if user else "-"
        default_notifier.info(
            f"User {username} searched for question {parameters['search']['all_field_query']}",
            user=user,
        )
    except Exception as e:
        logging.warn(f"Can't notify, {repr(e)}")

    serialized_data = SearchHistoryItemSerializer(instance=item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def update_search_history_item(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    # view is accesible without authentication

    try:
        data = json.loads(request.body)
        item_id: int = data["item_id"]
        total_matches: int = data["total_matches"]
        auto_relaxed: bool = data["auto_relaxed"]
        cluster_count: int = data["cluster_count"]
        result_information: dict = data["result_information"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = SearchHistoryItem.objects.get(id=item_id)
    except SearchHistoryItem.DoesNotExist:
        return HttpResponse(status=404)

    item.total_matches = total_matches
    item.auto_relaxed = auto_relaxed
    item.cluster_count = cluster_count
    item.result_information = result_information
    item.save()

    serialized_data = SearchHistoryItemSerializer(instance=item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def get_search_history(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
        limit: int = data.get("limit", 10)
        offset: int = data.get("offset", 0)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = SearchHistoryItem.objects.filter(user_id=request.user.id, organization_id=organization_id).order_by(
        "-created_at"
    )[offset : offset + limit : -1]
    serialized_data = SearchHistoryItemSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def add_collection(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
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

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def delete_collection(request):
    if request.method != "POST":
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
    if request.method != "POST":
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
        item.class_names = [class_name]
    elif class_name not in item.class_names:
        item.class_names.append(class_name)
    item.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def delete_collection_class(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    all_items = CollectionItem.objects.filter(collection_id=collection_id, classes__contains=[class_name])
    for item in all_items:
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
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        related_organization_id: int = data["related_organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = DataCollection.objects.filter(
        Q(related_organization_id=related_organization_id) & (Q(created_by=request.user.id) | Q(is_public=True))
    ).order_by("-created_at")
    serialized_data = CollectionSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def get_collection(request):
    if request.method != "POST":
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

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def set_collection_attributes(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        updates: dict = data["updates"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    allowed_fields = [
        "name",
        "notification_emails",
    ]

    for key in updates.keys():
        if key not in allowed_fields:
            return HttpResponse(status=400)

    for key, value in updates.items():
        setattr(collection, key, value)
    collection.save()

    collection_dict = CollectionSerializer(instance=collection).data
    result = json.dumps(collection_dict)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def get_trained_classifier(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        embedding_space_identifier: str = data["embedding_space_identifier"]
        include_vector: bool = data.get("include_vector", False)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        classifier = TrainedClassifier.objects.get(
            collection_id=collection_id,
            class_name=class_name,
            embedding_space=embedding_space_identifier,
        )
    except TrainedClassifier.DoesNotExist:
        result = json.dumps(None)
        return HttpResponse(result, status=200, content_type="application/json")
    if (
        classifier.collection.created_by != request.user
        and not classifier.collection.is_public
        and not is_from_backend(request)
    ):
        return HttpResponse(status=401)
    serialized_data = TrainedClassifierSerializer(classifier).data
    assert isinstance(serialized_data, dict)
    if not include_vector and "decision_vector" in serialized_data:
        serialized_data["decision_vector_exists"] = len(serialized_data["decision_vector"]) > 0
        del serialized_data["decision_vector"]
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def set_trained_classifier(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        embedding_space_identifier: str = data["embedding_space_identifier"]
        decision_vector = data.get("decision_vector")
        highest_score = data.get("highest_score")
        threshold = data.get("threshold")
        metrics = data.get("metrics")
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        classifier = TrainedClassifier.objects.get(
            collection_id=collection_id,
            class_name=class_name,
            embedding_space=embedding_space_identifier,
        )
    except TrainedClassifier.DoesNotExist:
        classifier = TrainedClassifier(
            collection_id=collection_id,
            class_name=class_name,
            embedding_space=embedding_space_identifier,
        )
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
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name = data["class_name"]
        field_type = data["type"]
        is_positive = data["is_positive"]
        offset = data.get("offset", 0)
        limit = data.get("limit", 25)
        order_by = data.get("order_by", "-date_added")
        include_column_data = data.get("include_column_data", False)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.select_related("most_recent_search_task").get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)

    return_items, reference_ds_and_item_id = get_filtered_collection_items(
        collection, class_name, field_type, is_positive, order_by
    )

    filtered_count = return_items.count()
    # filtered_item_ids is e.g. used to highlight items on the map:
    # TODO: check if this is a performance issue when no map is used
    filtered_item_ids = return_items.values_list("id", flat=True)

    return_items = return_items[offset : offset + limit]
    serialized_data = CollectionItemSerializer(return_items, many=True).data

    if not include_column_data:
        for item in serialized_data:
            item.pop("column_data", None)

    result = {
        "items": serialized_data,
        "items_last_changed": collection.items_last_changed.isoformat(),
        "search_mode": collection.search_mode,
        "filtered_count": filtered_count,
        "filtered_item_ids": list(filtered_item_ids),
    }
    result = json.dumps(result)

    return HttpResponse(result, status=200, content_type="application/json")


def get_filtered_collection_items(
    collection: DataCollection, class_name, field_type=None, is_positive=None, order_by="-date_added"
) -> tuple[BaseManager[CollectionItem], tuple[int, str] | None]:
    if field_type:
        all_items = CollectionItem.objects.filter(
            collection_id=collection.id,
            field_type=field_type,
            # is_positive=is_positive,  # FIXME: is_positive will be replaced by relevance
            classes__contains=[class_name],
        )
    else:
        # return all items
        all_items = CollectionItem.objects.filter(collection_id=collection.id, classes__contains=[class_name])

    reference_ds_and_item_id = None
    task: SearchTask | None = collection.most_recent_search_task
    if collection.search_mode:
        assert task is not None
        settings = SearchTaskSettings(**task.settings)
        if settings.reference_dataset_id and settings.reference_item_id:
            reference_ds_and_item_id = (settings.reference_dataset_id, settings.reference_item_id)

        search_results = all_items.filter(search_source_id=task.id)
        if collection.ui_settings.get("hide_checked_items_in_search"):
            search_results = search_results.filter(relevance=ItemRelevance.CANDIDATE)
        return_items = search_results
        return_items = return_items.order_by("-search_score")
    else:
        return_items = (
            all_items.filter(relevance__gte=ItemRelevance.APPROVED_BY_AI)
            if is_positive
            else all_items.filter(relevance__lte=ItemRelevance.REJECTED_BY_AI)
        )
        return_items = return_items.order_by(order_by, "-search_score")

    for filter_data in collection.filters:
        filter = CollectionFilter(**filter_data)
        if filter.filter_type == "collection_item_ids":
            return_items = return_items.filter(id__in=filter.value)
        elif filter.filter_type == "metadata_value_gte":
            return_items = return_items.filter(**{f"metadata__{filter.field}__gte": filter.value})
        elif filter.filter_type == "metadata_value_lte":
            return_items = return_items.filter(**{f"metadata__{filter.field}__lte": filter.value})
        elif filter.filter_type == "metadata_value_is":
            return_items = return_items.filter(**{f"metadata__{filter.field}": filter.value})
        elif filter.filter_type == "metadata_value_contains":
            return_items = return_items.filter(**{f"metadata__{filter.field}__contains": filter.value})
        elif filter.filter_type == "text_query":
            return_items = apply_text_filter(return_items, filter)

    return return_items, reference_ds_and_item_id


def apply_text_filter(items: BaseManager, filter: CollectionFilter) -> BaseManager:
    field = filter.field
    query = filter.value
    if field == "_descriptive_text_fields":
        example_dataset_id = next(e.dataset_id for e in items if e.dataset_id is not None)
        # FIXME: this uses only the first dataset id and won't work for multiple datasets
        dataset = Dataset.objects.get(id=example_dataset_id)
        fields = dataset.schema.descriptive_text_fields or []
        if fields and query:
            or_queries = [Q(**{f"metadata__{field}__icontains": query}) for field in fields]
            items = items.filter(reduce(operator.or_, or_queries))
    else:
        if field and query:
            items = items.filter(**{f"metadata__{field}__icontains": query})
    return items


@csrf_exempt
def get_related_collection_items(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        dataset_id: int = data["dataset_id"]
        item_id: str = data["item_id"]
        include_column_data: bool = data.get("include_column_data", False)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    all_items = CollectionItem.objects.filter(dataset_id=dataset_id, item_id=item_id)
    all_items = all_items.order_by("-date_added")
    serialized_data = CollectionItemSerializer(all_items, many=True).data
    if not include_column_data:
        for item in serialized_data:
            item.pop("column_data", None)
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def add_item_to_collection(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data.get("class_name", "_default")
        is_positive: bool = data["is_positive"]
        field_type: str = data["field_type"]
        value: str | None = data.get("value")
        dataset_id: int | None = data.get("dataset_id")
        item_id: str | None = data.get("item_id")
        weight: float = data.get("weight", 1.0)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    if value is None and dataset_id is None:
        return HttpResponse(status=400)
    if field_type == FieldType.IDENTIFIER and not (dataset_id is not None and item_id is not None):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user and not is_from_backend(request):
        return HttpResponse(status=401)

    items = CollectionItem.objects.filter(
        collection_id=collection_id,
        is_positive=is_positive,
        field_type=field_type,
        value=value,
        dataset_id=dataset_id,
        item_id=item_id,
    )

    exists = False
    for item in items:
        if class_name in item.classes:
            # the item exists already, but the weight might need to be updated:
            item.weight = weight
            item.save()
            exists = True
            break

    if not exists:
        item = CollectionItem()
        item.collection_id = collection_id  # type: ignore
        item.is_positive = is_positive
        item.classes = [class_name]
        item.field_type = field_type
        item.value = value
        item.dataset_id = dataset_id
        item.item_id = item_id
        item.weight = weight
        item.save()

    dataset_dict = CollectionItemSerializer(instance=item).data
    serialized_data = json.dumps(dataset_dict)

    collection.items_last_changed = timezone.now()
    collection.save()

    return HttpResponse(serialized_data, status=200, content_type="application/json")


@csrf_exempt
def set_collection_item_relevance(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_item_id: int = data["collection_item_id"]
        relevance: int = data["relevance"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection_item = CollectionItem.objects.get(id=collection_item_id)
    except CollectionItem.DoesNotExist:
        return HttpResponse(status=404)
    if collection_item.collection.created_by != request.user:
        return HttpResponse(status=401)

    collection_item.relevance = relevance
    collection_item.save()

    # TODO: check if actions need to be done for approved item

    return HttpResponse(None, status=204)


@csrf_exempt
def remove_collection_item(request):
    if request.method != "POST":
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

    collection_item.delete()

    # for class_name in collection_item.classes:
    collection_item.collection.items_last_changed = timezone.now()
    collection_item.collection.save(update_fields=["items_last_changed"])

    return HttpResponse(None, status=204)


@csrf_exempt
def remove_collection_item_by_value(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        value: str = data["value"]
        dataset_id: int = data["dataset_id"]
        item_id: str = data["item_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    collection_items = CollectionItem.objects.filter(
        collection_id=collection_id,
        value=value,
        dataset_id=dataset_id,
        item_id=item_id,
        classes__contains=[class_name],
    )
    if not collection_items:
        return HttpResponse(status=404)

    removed_items = []
    for item in collection_items:
        if item.collection.created_by != request.user:
            continue
        item_dict = CollectionItemSerializer(instance=item).data
        removed_items.append(item_dict)
        item.delete()

    collection.items_last_changed = timezone.now()
    collection.save(update_fields=["items_last_changed"])

    serialized_data = json.dumps(removed_items)

    return HttpResponse(serialized_data, status=200, content_type="application/json")


@csrf_exempt
def add_stored_map(request):
    if request.method != "POST":
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
    item.map_data = map_data.encode()  # FIXME: base64 str needs to be decoded
    item.save()

    serialized_data = StoredMapSerializer(instance=item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def get_stored_maps(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    # TODO: also show public ones
    items = StoredMap.objects.filter(user_id=request.user.id, organization_id=organization_id).order_by("created_at")[
        :25
    ]
    serialized_data = StoredMapSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def get_stored_map_data(request):
    if request.method != "POST":
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
    result = map_item.map_data

    return HttpResponse(result, status=200, content_type="application/octet-stream")


@csrf_exempt
def delete_stored_map(request):
    if request.method != "POST":
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
    if request.method != "POST":
        return HttpResponse(status=405)

    items = Generator.objects.all()
    serialized_data = GeneratorSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type="application/json")


@csrf_exempt
def remove_items(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        dataset_id = data["dataset_id"]
        item_ids = data["item_ids"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        dataset: Dataset = Dataset.objects.get(id=dataset_id)
        dataset.remove_items(item_ids)
    except Dataset.DoesNotExist:
        return HttpResponse(status=404)
    except Exception as e:
        logging.error(e)
        return HttpResponse(status=500)

    return HttpResponse(status=204)


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

    for field in dataset.schema.object_fields:
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
