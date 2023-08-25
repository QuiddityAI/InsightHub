import json

from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import FieldType, Organization, ObjectSchema, ObjectField


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"


@login_required()
@csrf_exempt
def get_organizations(request):
    if request.method != 'GET':
        return HttpResponse(status=405)

    all_objects = Organization.objects.all()
    result = serializers.serialize('json', all_objects)

    return HttpResponse(result, status=200, content_type='application/json')

"""
def get_generator_function(name, parameters) -> function:
    pass


@csrf_exempt
def add_elements(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)

    schema_id: str = data["schema_id"]  # TODO: catch error
    schema: ObjectSchema = ObjectSchema.objects.get(id=schema_id)  # TODO: catch error
    # TODO: check if sender is allowed to add data to this schema / organization

    fields: list[ObjectField] = ObjectField.objects.filter(schema=schema_id)

    # TODO: check if table in Mongo exists
    # if not, create it and mark filterable fields as indexed

    pipeline_steps = []
    for field in fields:
        if field.should_be_generated:
            dependencies = field.source_fields
            # TODO


    # TODO: check generate_if_not_exits and skip_generators settings

    batch = data["elements"]

    # [ (generator: summary, target field: summary_ai, element_ids: (id, id), source field data: (data, data)) ]

    for element in batch:
        # TODO: check required, non-generatable fields
        pass

    for pipeline_step in pipeline_steps:
        element_indexes = []
        source_data_total = []
        # TODO: condition_func = eval(pipeline_step["generating_condition"])

        for i, element in enumerate(batch):
            element_indexes.append(i)
            source_data = []
            # TODO: if not condition(element): continue
            for source_field in pipeline_step["source_fields"]:
                source_data.append(element[source_field])
            source_data_total.append(source_data)

        generator_func = get_generator_function(pipeline_step["generator_name"], pipeline_step["generator_parameters"])

        results = generator_func(element_indexes, source_data_total)

        for element_index, result in zip(element_indexes, results):
            batch[element_index][pipeline_step["target_field"]] = result

    for element in batch:
        # TODO: store in MongoDB
        pass



    return HttpResponse(status=204, content_type='application/json')


@csrf_exempt
def update_elements(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)

    schema_id: str = data["schema_id"]  # TODO: catch error
    schema: ObjectSchema = ObjectSchema.objects.get(id=schema_id)  # TODO: catch error
    # TODO: check if sender is allowed to add data to this schema / organization

    fields: list[ObjectField] = ObjectField.objects.filter(schema=schema_id)

    pipeline_steps = []
    steps_added = []
    any_field_skipped = True
    while any_field_skipped:  # FIXME: endless loop if circular dependency
        phase_steps = []
        any_field_skipped = False
        for field in fields:
            if field in steps_added: continue
            this_field_skipped = False
            if field.should_be_generated:
                dependencies = field.source_fields
                for dep in dependencies:
                    if dep.should_be_generated and dep not in steps_added:
                        this_field_skipped = True
                        break
                if this_field_skipped:
                    any_field_skipped = True
                    continue
                phase_steps.append({
                    'source_fields': field.source_fields,
                    'generator_name': field.generator.name,
                    'generator_parameters': field.generator_parameters,
                    'target_field': field.identifier,
                })
                steps_added.append(field)
        if phase_steps:
            pipeline_steps.append(phase_steps)

    # TODO: check generate_if_not_exits and skip_generators settings

    batch = data["elements"]

    # [ (generator: summary, target field: summary_ai, element_ids: (id, id), source field data: (data, data)) ]

    # getting internal id from mongo using primary_key_field needs that field to be indexed
    # in Mongo, which it might not be
    primary_key_field: str = data["primary_key_field"]  # TODO: catch error
    primary_keys = []

    for element in batch:
        primary_keys.append(element[primary_key_field])

    current_versions = []  # TODO: mongo.get(schema=schema_id, where primary_key_field in primary_key)
    # alternatively: rely on changed_fields parameter (provided by sender, same for all elements)
    # alternatively: rely on only fields being present that changed -> changed_fields = new_element.keys()

    changed_fields_total = []
    for new_element, current_element in zip(batch, current_versions):
        changed_fields = []
        for field in new_element.keys():
            if new_element[field] != current_element.get(field):
                changed_fields.append(field)
        changed_fields_total.append(changed_fields)

    for phase in pipeline_steps:
        for pipeline_step in phase:  # TODO: this can be done in parallel
            element_indexes = []
            source_data_total = []
            # TODO: condition_func = eval(pipeline_step["generating_condition"])

            for i, element in enumerate(batch):
                if not set(changed_fields_total[i]) & set(pipeline_step["source_fields"]): continue
                # TODO: if not condition(element): continue
                element_indexes.append(i)
                source_data = []
                for source_field in pipeline_step["source_fields"]:
                    source_data.append(element[source_field])
                source_data_total.append(source_data)

            generator_func = get_generator_function(pipeline_step["generator_name"], pipeline_step["generator_parameters"])

            results = generator_func(source_data_total)

            for element_index, result in zip(element_indexes, results):
                batch[element_index][pipeline_step["target_field"]] = result
                changed_fields_total[element_index].append(pipeline_step["target_field"])

    for element in batch:
        # TODO: upsert in MongoDB
        pass

    vector_db_fields = []
    text_db_fields = []
    filtering_fields = []

    for field in fields:
        if field.is_available_for_search and field.field_type == FieldType.VECTOR:
            vector_db_table_name = f'{schema.id}_{field.identifier}'
            vector_db_fields.append([field.identifier, vector_db_table_name])
        elif field.is_available_for_search and field.field_type == FieldType.TEXT:
            text_db_table_name = f'{schema.id}_{field.identifier}'
            text_db_fields.append([field.identifier, text_db_table_name])

        if field.is_available_for_filtering:
            filtering_fields.append(field.identifier)

    # TODO: ensure the tables exist
    # TODO: skip if no indexed fields

    for element in batch:
        # TODO: if no intersection between db_fields and changed_fields: continue
        filtering_attributes = {}
        for field in filtering_fields:
            filtering_attributes[field] = element[field]
        for field, table in vector_db_fields:
            # qdrant.upsert(table: table, id: element.id, vector: element[field], attributes: filtering_attributes)
            pass
        for field, table in text_db_fields:
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