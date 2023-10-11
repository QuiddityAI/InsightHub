import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import ObjectSchema, SearchHistoryItem, ItemCollection, StoredMap, Generator
from .serializers import ObjectSchemaSerializer, SearchHistoryItemSerializer, ItemCollectionSerializer, StoredMapSerializer, GeneratorSerializer


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"


@csrf_exempt
def get_health(request):
    return HttpResponse("", status=200)


#@login_required()
@csrf_exempt
def get_object_schema(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        schema_id: int = data["schema_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    schema: ObjectSchema = ObjectSchema.objects.get(id=schema_id)
    # TODO: check permission to read this object

    schema_dict = ObjectSchemaSerializer(instance=schema).data
    schema_dict["object_fields"] = {item['identifier']: item for item in schema_dict["object_fields"]}

    result = json.dumps(schema_dict)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def get_available_schemas(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        organization_id: int = data["organization_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    #schemas = ObjectSchema.objects.get(organization=organization_id)
    schemas = ObjectSchema.objects.all()  # FIXME: returning all for now for testing
    # TODO: check permission to read this object

    result = []
    for schema in schemas:
        result.append({"id": schema.id, "name": schema.name,  # type: ignore
                       "name_plural": schema.name_plural, "short_description": schema.short_description})

    result = json.dumps(result)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def add_search_history_item(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        schema_id: int = data["schema_id"]
        name: str = data["name"]
        parameters: dict = data["parameters"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    item = SearchHistoryItem()
    item.user_id = user_id  # type: ignore
    item.schema_id = schema_id  # type: ignore
    item.name = name
    item.parameters = parameters  # type: ignore
    item.save()

    serialized_data = SearchHistoryItemSerializer(instance=item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def get_search_history(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        schema_id: int = data["schema_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = SearchHistoryItem.objects.filter(user_id=user_id, schema_id=schema_id).order_by('-created_at')[:25:-1]
    serialized_data = SearchHistoryItemSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def add_item_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        schema_id: int = data["schema_id"]
        name: str = data["name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    item = ItemCollection()
    item.user_id = user_id  # type: ignore
    item.schema_id = schema_id  # type: ignore
    item.name = name
    item.save()

    schema_dict = ItemCollectionSerializer(instance=item).data
    result = json.dumps(schema_dict)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def get_item_collections(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        schema_id: int = data["schema_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = ItemCollection.objects.filter(user_id=user_id, schema_id=schema_id).order_by('created_at')[:25]
    serialized_data = ItemCollectionSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def get_item_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = ItemCollection.objects.get(id=collection_id)
    except ItemCollection.DoesNotExist:
        return HttpResponse(status=404)
    serialized_data = ItemCollectionSerializer(item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def delete_item_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        ItemCollection.objects.get(id=collection_id).delete()
    except ItemCollection.DoesNotExist:
        return HttpResponse(status=404)

    return HttpResponse(None, status=204)


#@login_required()
@csrf_exempt
def add_item_to_collection(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        item_id: str = data["item_id"]
        is_positive: bool = data["is_positive"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = ItemCollection.objects.get(id=collection_id)
    except ItemCollection.DoesNotExist:
        return HttpResponse(status=404)

    if is_positive:
        if collection.positive_ids is None:
            collection.positive_ids = []
        collection.positive_ids.append(item_id)
    else:
        if collection.negative_ids is None:
            collection.negative_ids = []
        collection.negative_ids.append(item_id)
    collection.save()

    return HttpResponse(None, status=204)


#@login_required()
@csrf_exempt
def add_stored_map(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        schema_id: int = data["schema_id"]
        name: str = data["name"]
        map_id: str = data["map_id"]
        map_data: str = data["map_data"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    item = StoredMap(id=map_id)
    item.user_id = user_id  # type: ignore
    item.schema_id = schema_id  # type: ignore
    item.name = name
    item.map_data = map_data.encode()  # type: ignore  # FIXME: base64 str needs to be decoded
    item.save()

    serialized_data = StoredMapSerializer(instance=item).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def get_stored_maps(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        schema_id: int = data["schema_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    items = StoredMap.objects.filter(user_id=user_id, schema_id=schema_id).order_by('created_at')[:25]
    serialized_data = StoredMapSerializer(items, many=True).data
    result = json.dumps(serialized_data)

    return HttpResponse(result, status=200, content_type='application/json')


#@login_required()
@csrf_exempt
def get_stored_map_data(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

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

    return HttpResponse(result, status=200, content_type='application/octet-stream')


#@login_required()
@csrf_exempt
def delete_stored_map(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        stored_map_id: int = data["stored_map_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        StoredMap.objects.get(id=stored_map_id).delete()
    except StoredMap.DoesNotExist:
        return HttpResponse(status=404)

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


def get_changed_fields(primary_key_field, batch, schema):
    # getting internal id from mongo using primary_key_field needs that field to be indexed
    # in Mongo, which it might not be
    primary_keys = []

    for element in batch:
        primary_keys.append(element[primary_key_field])

    current_versions = []  # TODO: mongo.get(schema=schema_id, where primary_key_field in primary_key)
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


def get_index_settings(schema):
    vector_db_fields = []
    text_db_fields = []
    filtering_fields = []

    for field in schema.object_fields:
        if field.is_available_for_search and field.field_type == FieldType.VECTOR:
            vector_db_table_name = f'{schema.id}_{field.identifier}'
            vector_db_fields.append([field.identifier, vector_db_table_name])
        elif field.is_available_for_search and field.field_type == FieldType.TEXT:
            text_db_table_name = f'{schema.id}_{field.identifier}'
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

    schema_id: str = data["schema_id"]  # TODO: catch error
    schema: ObjectSchema = get_object_schema(schema_id)

    # TODO: check generate_if_not_exits and skip_generators settings
    pipeline_steps = get_pipeline_steps()

    batch = data["elements"]

    changed_fields_total = get_changed_fields(primary_key_field, batch, schema)

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

    index_settings = get_index_settings(schema)

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


def generate_field_for_existing_elements(schema_id, field_name, force_recreation):

    # TODO: create Task object for this
    # TODO: get all ids once (to handle that new items may come in during the processing time, but those are handled there)
    # TODO: split up in batches, store current batch number in Task, show progress
    # TODO: do in background thread

    schema: ObjectSchema = ObjectSchema.objects.get(id=schema_id)  # TODO: catch error
    # TODO: check if sender is allowed to change data on this schema / organization
    fields: list[ObjectField] = ObjectField.objects.filter(schema=schema_id)
    pipeline_steps = None  # get_pipeline_steps(fields, restrict_to=[field_name])

    all_elements = None  # mongo.get(where schema_id is schema_id)

    for step in pipeline_steps:
        # do same as above, but instead of changed_fields for source fields, check if field is empty or force_recreation
        # for element in all_elements: ...
        pass


def get_elements(ids, schema_id, generate_if_not_exist_fields=[]):
    results = []  # mongo.get(where id in ids)
    schema: ObjectSchema = ObjectSchema.objects.get(id=schema_id)  # TODO: catch error
    # TODO: check if sender is allowed to get data from this schema / organization
    fields: list[ObjectField] = ObjectField.objects.filter(schema=schema_id)

    pipeline_steps = None  # get_pipeline_steps(fields, restrict_to=generate_if_not_exist_fields)

    for step in pipeline_steps:
        # do same as above, but instead of changed_fields for source fields, check if field is empty
        # for element in results: ...
        pass

    # commit result to mongo DB and indexes

    return results


def search_by_text_vectorized(schema_id, field_name, query_text):
    results = []  # mongo.get(where id in ids)
    schema: ObjectSchema = ObjectSchema.objects.get(id=schema_id)  # TODO: catch error
    # TODO: check if sender is allowed to get data from this schema / organization
    field: ObjectField = ObjectField.objects.filter(schema=schema_id, name=field_name)

    generator_func = get_generator_function(field.generator.name, field.generator_parameters)
    vector = generator_func([query_text])[0]
    vector_db_table_name = f'{schema.id}_{field.identifier}'

    # TODO: add filter criteria

    result_ids = None  # qdrant.find_near(vector_db_table_name, vector, limit)

    # add distances to results if not there yet

    objects = None  # mongo.get(where id in ids)
    # this could be slow if abstracts are retrieved, too

    return objects


def get_map_by_text_query_vectorized(schema_id, field_name, query_text):
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