from uuid import uuid4
import logging

from ..database_client.django_client import get_dataset
from ..database_client.vector_search_engine_client import VectorSearchEngineClient
from ..database_client.text_search_engine_client import TextSearchEngineClient
from ..logic.extract_pipeline import get_pipeline_steps

from data_map_backend.utils import DotDict, pk_to_uuid_id
from ..utils.field_types import FieldType


def update_database_layout(dataset_id: int):
    dataset = get_dataset(dataset_id)
    vector_db_client = VectorSearchEngineClient.get_instance()
    index_settings = get_index_settings(dataset)
    for field in index_settings.all_vector_fields:
        if not dataset.schema.object_fields[field].is_available_for_search:
            continue
        vector_db_client.ensure_dataset_field_exists(dataset, field, update_params=True, delete_if_params_changed=False)
    search_engine_client = TextSearchEngineClient.get_instance()
    search_engine_client.ensure_dataset_exists(dataset)


def insert_many(dataset_id: int, elements: list[dict], skip_generators: bool=False) -> list[tuple]:
    dataset = get_dataset(dataset_id)

    for element in elements:
        # make sure primary key exists, if not, generate it
        if not "_id" in element:
            if dataset.schema.primary_key in element and element[dataset.schema.primary_key] != "":
                element["_id"] = pk_to_uuid_id(element[dataset.schema.primary_key])
            else:
                element["_id"] = str(uuid4())
        elif isinstance("_id", int):
            element["_id"] = str(element["_id"])

    direct_parent_field: str = dataset.schema.direct_parent
    if direct_parent_field:
        for element in elements:
            direct_parent = element.get(direct_parent_field)
            if direct_parent:
                element["_parent"] = pk_to_uuid_id(direct_parent)

    all_parents_field = dataset.schema.all_parents
    if all_parents_field:
        for element in elements:
            all_parents = element.get(all_parents_field)
            if all_parents:
                element["_all_parents"] = [pk_to_uuid_id(parent) for parent in all_parents]

    # for upsert / update case: get changed fields:
    # changed_fields_total = get_changed_fields(primary_key_field, elements, dataset)

    if skip_generators:
        pipeline_steps = []
    else:
        pipeline_steps, _, _ = get_pipeline_steps(dataset)

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

                source_data: list | dict = []
                if pipeline_step.requires_multiple_input_fields:
                    assert isinstance(pipeline_step.source_fields, dict)
                    # pipeline_step.source_fields maps generator input -> source_field
                    source_data = {}
                    for generator_input, source_field in pipeline_step.source_fields.items():
                        source_data[generator_input] = element.get(source_field, None)
                    source_data = source_data
                else:
                    for source_field in pipeline_step.source_fields:
                        if source_field in element and element[source_field] is not None:
                            source_data.append(element[source_field])

                if source_data:
                    element_indexes.append(i)
                    source_data_total.append(source_data)

            results = pipeline_step.generator_function(source_data_total)

            if pipeline_step.returns_multiple_fields:
                for element_index, result in zip(element_indexes, results):
                    target_field_value, result_dict = result
                    elements[element_index][pipeline_step.target_field] = target_field_value
                    if not result_dict:
                        # e.g. when an error happened during the generation
                        continue
                    for output_field, item_field in pipeline_step.output_to_item_mapping.items():
                        elements[element_index][item_field] = result_dict[output_field]
            else:
                for element_index, result in zip(element_indexes, results):
                    elements[element_index][pipeline_step.target_field] = result

    for field in dataset.schema.object_fields.values():
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

    index_settings = get_index_settings(dataset)

    vector_db_client = VectorSearchEngineClient.get_instance()

    # first store all vectors in vector DB, so that we can then delete them from the elements
    # and pass the rest to OpenSearch:
    for vector_field in index_settings.all_vector_fields:
        ids = []
        vectors = []
        payloads = []
        for element in elements:
            if vector_field not in element or element[vector_field] is None:
                continue
            if len(element[vector_field]) == 0:
                # this is a multi-vector field but without any vectors
                continue
            ids.append(element['_id'])
            vectors.append(element[vector_field])

            filtering_attributes = {}
            for filtering_field in index_settings.filtering_fields:
                filtering_attributes[filtering_field] = element.get(filtering_field)
            payloads.append(filtering_attributes)

        if vectors:
            vector_db_client.upsert_items(dataset.actual_database_name, vector_field, ids, payloads, vectors)

    for element in elements:
        for vector_field in index_settings.all_vector_fields:
            if vector_field in element:
                del element[vector_field]

    search_engine_client = TextSearchEngineClient.get_instance()
    search_engine_client.upsert_items(dataset.actual_database_name, [item["_id"] for item in elements], elements)
    return [(dataset.id, item["_id"]) for item in elements]


def insert_vectors(dataset_id: int, vector_field: str, item_pks: list[str], vectors: list[list[float]], excluded_filter_fields: list[str] = []):
    """ Allows to insert vectors for items that are already in the database.
    The caller needs to take care of the best batch size itself."""
    dataset = get_dataset(dataset_id)
    # this assumes that the item_pks are not the item._id ids and still need to be converted:
    item_ids = [pk_to_uuid_id(item_pk) for item_pk in item_pks]

    index_settings = get_index_settings(dataset)

    text_storage_client = TextSearchEngineClient.get_instance()
    filter_fields = index_settings.vector_filtering_fields - set(excluded_filter_fields)
    filtering_data = text_storage_client.get_items_by_ids(dataset, item_ids, filter_fields)
    # takes 450ms for 512 items
    for filtering_data_item in filtering_data:
        filtering_data_item.pop("_id")
        filtering_data_item.pop("_dataset_id")

    vector_db_client = VectorSearchEngineClient.get_instance()
    vector_db_client.upsert_items(dataset.actual_database_name, vector_field, item_ids, filtering_data, vectors)
    # takes 120ms for 512 items (the other operations are negligible)


def get_index_settings(dataset: DotDict):
    all_vector_fields = []
    filtering_fields = []
    vector_filtering_fields = []

    for field in dataset.schema.object_fields.values():
        if field.field_type == FieldType.VECTOR:
            all_vector_fields.append(field.identifier)

        if field.is_available_for_filtering:
            filtering_fields.append(field.identifier)
            if not (field.index_parameters or {}).get('exclude_from_vector_database'):
                vector_filtering_fields.append(field.identifier)

    result = {
        'all_vector_fields': set(all_vector_fields),
        'filtering_fields': set(filtering_fields),
        'vector_filtering_fields': set(vector_filtering_fields),
        }

    return DotDict(result)


def delete_dataset_content(dataset_id: int):
    dataset = get_dataset(dataset_id)

    logging.warning(f"Deleting all data from dataset {dataset.name}, ID {dataset.id}, database name {dataset.actual_database_name}.")

    vector_db_client = VectorSearchEngineClient.get_instance()
    index_settings = get_index_settings(dataset)
    for field in index_settings.all_vector_fields:
        is_array_field = dataset.schema.object_fields[field].is_array
        vector_db_client.delete_field(dataset.actual_database_name, field, is_array_field)
    search_engine_client = TextSearchEngineClient.get_instance()
    search_engine_client.remove_dataset(dataset)
