import uuid
from uuid import uuid4, uuid5

from database_client.django_client import get_object_schema
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.text_search_engine_client import TextSearchEngineClient
from logic.extract_pipeline import get_pipeline_steps

from utils.dotdict import DotDict
from utils.field_types import FieldType


def update_database_layout(schema_id: int):
    schema = get_object_schema(schema_id)
    vector_db_client = VectorSearchEngineClient.get_instance()
    index_settings = get_index_settings(schema)
    for field in index_settings.indexed_vector_fields:
        vector_db_client.ensure_schema_exists(schema, field, update_params=True, delete_if_params_changed=False)
    search_engine_client = TextSearchEngineClient.get_instance()
    search_engine_client.ensure_schema_exists(schema)


def insert_many(schema_id: int, elements: list[dict]):
    schema = get_object_schema(schema_id)

    for element in elements:
        # make sure primary key exists, if not, generate it
        if not "_id" in element:
            if schema.primary_key in element and element[schema.primary_key] != "":
                element["_id"] = str(uuid5(uuid.NAMESPACE_URL, element[schema.primary_key]))
            else:
                element["_id"] = str(uuid4())
        elif isinstance("_id", int):
            element["_id"] = str(element["_id"])

    # for upsert / update case: get changed fields:
    # changed_fields_total = get_changed_fields(primary_key_field, elements, schema)

    pipeline_steps, _ = get_pipeline_steps(schema)

    for phase in pipeline_steps:
        for pipeline_step in phase:  # TODO: this could be done in parallel
            pipeline_step = DotDict(pipeline_step)
            element_indexes = []
            source_data_total = []

            for i, element in enumerate(elements):
                # for insert case: check if field is already filled in, skip it in that case:
                if pipeline_step.target_field in element and element[pipeline_step.target_field] is not None:
                    continue

                # for update case: check if the fields in question changed:
                # if not set(changed_fields_total[i]) & set(pipeline_step["source_fields"]):
                #     continue

                if (pipeline_step.condition_function is not None
                    and not pipeline_step.condition_function(element)):
                    continue

                element_indexes.append(i)
                source_data = []
                for source_field in pipeline_step.source_fields:
                    if source_field in element:
                        source_data.append(element[source_field])
                source_data_total.append(source_data)

            results = pipeline_step.generator_function(source_data_total)

            for element_index, result in zip(element_indexes, results):
                elements[element_index][pipeline_step.target_field] = result
                # for update case: add that field to changed fields:
                # changed_fields_total[element_index].insert(pipeline_step.target_field)

    for field in schema.object_fields.values():
        if field.field_type == FieldType.CLASS_PROBABILITY and not field.is_array:
            for element  in elements:
                if field.identifier not in element:
                    continue
                # values less or equal zero are not supported by OpenSearch
                element[field.identifier] = max(element[field.identifier], 0.00001)
        elif field.field_type == FieldType.CLASS_PROBABILITY and field.is_array:
            for element  in elements:
                if field.identifier not in element or not isinstance(element[field.identifier], dict):
                    continue
                # values less or equal zero are not supported by OpenSearch
                element[field.identifier] = {k: max(v, 0.00001) for k, v in element[field.identifier].items()}

    search_engine_client = TextSearchEngineClient.get_instance()
    # TODO: exclude vectors that are stored in vector DB (what if that setting changes?)
    search_engine_client.upsert_items(schema.id, [item["_id"] for item in elements], elements)

    index_settings = get_index_settings(schema)

    vector_db_client = VectorSearchEngineClient.get_instance()

    for vector_field in index_settings.indexed_vector_fields:
        ids = []
        vectors = []
        payloads = []
        for element in elements:
            if vector_field not in element or element[vector_field] is None:
                continue
            ids.append(element['_id'])
            vectors.append(element[vector_field])

            filtering_attributes = {}
            for filtering_field in index_settings.filtering_fields:
                filtering_attributes[filtering_field] = element.get(filtering_field)
            payloads.append(filtering_attributes)

        if vectors:
            vector_db_client.upsert_items(schema.id, vector_field, ids, payloads, vectors)


def get_index_settings(schema: DotDict):
    indexed_vector_fields = []
    indexed_text_fields = []
    filtering_fields = []

    for field in schema.object_fields.values():
        if field.is_available_for_search and field.field_type == FieldType.VECTOR:
            indexed_vector_fields.append(field.identifier)
        elif field.is_available_for_search and field.field_type == FieldType.TEXT:
            indexed_text_fields.append(field.identifier)

        if field.is_available_for_filtering:
            filtering_fields.append(field.identifier)

    result = {
        'indexed_vector_fields': indexed_vector_fields,
        'indexed_text_fields': indexed_text_fields,
        'filtering_fields': filtering_fields
        }

    return DotDict(result)
