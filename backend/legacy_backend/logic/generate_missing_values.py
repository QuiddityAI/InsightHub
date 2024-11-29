from collections import defaultdict
import logging
import time
from typing import Callable

from ..database_client.django_client import get_dataset
from ..database_client.vector_search_engine_client import VectorSearchEngineClient
from ..database_client.text_search_engine_client import TextSearchEngineClient

from ..logic.extract_pipeline import get_pipeline_steps
from ..logic.insert_logic import get_index_settings, update_database_layout
from ..logic.search_common import separate_text_and_vector_fields, fill_in_vector_data_list

from data_map_backend.utils import DotDict
from ..utils.field_types import FieldType

from data_map_backend.models import GenerationTask
from data_map_backend.views.other_views import get_serialized_dataset_cached


def delete_field_content(dataset_id: int, field_identifier: str):
    dataset = get_dataset(dataset_id)
    is_vector_field = dataset.schema.object_fields[field_identifier].field_type == FieldType.VECTOR
    if is_vector_field:
        is_array_field = dataset.schema.object_fields[field_identifier].is_array
        vector_db_client = VectorSearchEngineClient.get_instance()
        vector_db_client.delete_field(dataset.actual_database_name, field_identifier, is_array_field)
    else:
        search_engine_client = TextSearchEngineClient.get_instance()
        search_engine_client.delete_field(dataset.actual_database_name, field_identifier)


def generate_missing_values(task: GenerationTask):
    task.log = ""
    task.save()
    logging.warning(f"Generating missing values for dataset {task.dataset}, field {task.field}...")
    task.add_log(f"Generating missing values for dataset {task.dataset}, field {task.field}...")
    dataset_id: int = task.dataset.id  # type: ignore
    field_identifier: str = task.field.identifier
    dataset = get_serialized_dataset_cached(dataset_id)

    # the field to be filled in might not have the necessary database columns yet:
    # update_database_layout(dataset_id)
    # TODO: store time of last layout update in dataset and compare with date of last change

    if task.regenerate_all:
        task.add_log(f"Deleting content of field {field_identifier} because all items should be regenerated")
        delete_field_content(dataset_id, field_identifier)
        task.add_log(f"Deleted content of field {field_identifier}")

    pipeline_steps, required_fields, potentially_changed_fields = get_pipeline_steps(dataset, only_fields=[field_identifier])
    potentially_changed_text_fields, potentially_changed_vector_fields = separate_text_and_vector_fields(dataset, potentially_changed_fields)
    task.add_log(f"The following fields will potentially be changed: text fields {potentially_changed_text_fields}, vector fields {potentially_changed_vector_fields}")
    index_settings = get_index_settings(dataset)
    if potentially_changed_vector_fields or (potentially_changed_fields & index_settings.filtering_fields):
        # if vector fields change, all filtering fields are required during the update:
        # (same if a filtering field changes, then the other fields might be required for a full update of the payload in qdrant)
        # TODO: remove when qdrant isn't used anymore
        required_fields |= index_settings.filtering_fields
    required_text_fields, required_vector_fields = separate_text_and_vector_fields(dataset, required_fields)
    task.add_log(f"The following fields will be retrieved: text fields {required_text_fields}, vector fields {required_vector_fields}")

    search_engine_client = TextSearchEngineClient.get_instance()
    vector_db_client = VectorSearchEngineClient.get_instance()
    items_processed = 0
    total_items_estimated = search_engine_client.get_all_items_with_missing_field_count(dataset.actual_database_name, field_identifier)
    is_vector_field = dataset.schema.object_fields[field_identifier].field_type == FieldType.VECTOR
    is_array_field = dataset.schema.object_fields[field_identifier].is_array
    if is_vector_field:
        total_items_estimated -= vector_db_client.get_item_count(dataset, field_identifier)
    task.add_log(f"Total items with missing value: {total_items_estimated}")
    if total_items_estimated == 0:
        task.add_log(f"Nothing to do")
        return

    def _process(elements):
        nonlocal items_processed
        t1 = time.time()
        changed_fields = generate_missing_values_for_given_elements(pipeline_steps, elements, task.add_log)
        t2 = time.time()
        generation_duration = t2 - t1
        _update_indexes_with_generated_values(dataset, elements, changed_fields)
        index_update_duration = time.time() - t2
        duration = generation_duration + index_update_duration
        items_processed += len(elements)
        task.add_log(f"Processed {items_processed} of {total_items_estimated} ({(items_processed / float(total_items_estimated)) * 100:.1f} %)")
        task.add_log(f"Time per item: generation {generation_duration / len(elements) * 1000:.2f} ms, index update {index_update_duration / len(elements) * 1000:.2f} ms, total {duration / len(elements) * 1000:.2f} ms")
        task.add_log(f"Estimated remaining time: {(duration / len(elements) * (total_items_estimated - items_processed)) / 60.0:.1f} min")

    batch_size = 512

    generator = search_engine_client.get_all_items_with_missing_field(dataset.actual_database_name, field_identifier, required_text_fields, internal_batch_size=batch_size)
    elements = []
    last_batch_time = time.time()
    skipped_items = 0
    for element in generator:
        elements.append(element)
        if len(elements) % batch_size == 0:
            if is_vector_field:
                items_where_vector_already_exists = vector_db_client.get_items_by_ids(
                    dataset, [x["_id"] for x in elements], field_identifier, is_array_field, return_payloads=False, return_vectors=False)
                if len(items_where_vector_already_exists) == len(elements):
                    skipped_items += len(elements)
                    elements = []
                    last_batch_time = time.time()
                    task.add_log(f"Skipping batch, skipped {skipped_items}")
                    continue
                for item in items_where_vector_already_exists:
                    # TODO: there might be a faster way to do this
                    for i, element in reversed(list(enumerate(elements))):
                        if element["_id"] == item.id:
                            skipped_items += 1
                            del elements[i]
            if required_vector_fields:
                fill_in_vector_data_list(dataset, elements, required_vector_fields)
            element_retrieval_time = time.time() - last_batch_time
            task.add_log(f"Time to retrieve {len(elements)} items: {element_retrieval_time * 1000:.2f} ms")
            _process(elements)
            elements = []
            last_batch_time = time.time()
    if elements:
        # process remaining elements
        if required_vector_fields:
            fill_in_vector_data_list(dataset, elements, required_vector_fields)
        element_retrieval_time = time.time() - last_batch_time
        task.add_log(f"Time to retrieve {len(elements)} items: {element_retrieval_time * 1000:.2f} ms")
        _process(elements)
    logging.warning(f"Done")
    task.add_log(f"Done")


def generate_missing_values_for_given_elements(pipeline_steps: list[list[dict]], elements: list[dict], log_error: Callable) -> dict:
    # when adapting this function, also adapt insert_many() in insert_logic.py
    changed_fields = defaultdict(set)
    for phase in pipeline_steps:
        for pipeline_step in phase:  # TODO: this could be done in parallel
            pipeline_step = DotDict(pipeline_step)
            element_indexes = []
            source_data_total = []

            for i, element in enumerate(elements):
                # if field is already filled in, skip it:
                if pipeline_step.target_field in element and element[pipeline_step.target_field] is not None:
                    continue

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

            results = pipeline_step.generator_function(source_data_total, log_error)

            if pipeline_step.returns_multiple_fields:
                for element_index, result in zip(element_indexes, results):
                    target_field_value, result_dict = result
                    elements[element_index][pipeline_step.target_field] = target_field_value
                    if not result_dict:
                        # e.g. when an error happened during the generation
                        continue
                    for output_field, item_field in pipeline_step.output_to_item_mapping.items():
                        elements[element_index][item_field] = result_dict[output_field]
                        changed_fields[element_index].add(item_field)
            else:
                for element_index, result in zip(element_indexes, results):
                    elements[element_index][pipeline_step.target_field] = result
                    changed_fields[element_index].add(pipeline_step.target_field)
    return changed_fields  # elements is changed in-place


def _update_indexes_with_generated_values(dataset, elements, changed_fields):
    # Attention: this method may delete content of 'elements'!
    index_settings = get_index_settings(dataset)

    vector_db_client = VectorSearchEngineClient.get_instance()

    for vector_field in index_settings.all_vector_fields:
        ids = []
        vectors = []
        payloads = []
        for element_index, element in enumerate(elements):
            if vector_field not in changed_fields[element_index] \
                and len(changed_fields[element_index] & index_settings.filtering_fields) == 0:
                # TODO: if only a filtering field changed, the other filtering fields might not be present (currently they are)
                # Does qdrant support a partial update on the payload? Or does it replace the payload? If it can, then other fields are not required
                continue
            if vector_field not in element or element[vector_field] is None:
                continue
            ids.append(element['_id'])
            vectors.append(element[vector_field])

            filtering_attributes = {}
            for filtering_field in index_settings.filtering_fields:
                filtering_attributes[filtering_field] = element.get(filtering_field)
            payloads.append(filtering_attributes)

        if vectors:
            vector_db_client.upsert_items(dataset.actual_database_name, vector_field, ids, payloads, vectors)

    # Question: Does OpenSearch upsert actually only update provided fields or does it delete the other fields?
    # -> yes, it only updates the provided fields
    text_search_updates = []
    for element_index, element in enumerate(elements):
        changed_non_vector_fields = changed_fields[element_index] - index_settings.all_vector_fields
        if not changed_non_vector_fields:
            continue
        updated_element = {field: v for field, v in element.items() if field in changed_non_vector_fields}
        updated_element["_id"] = element["_id"]
        text_search_updates.append(updated_element)

    if text_search_updates:
        search_engine_client = TextSearchEngineClient.get_instance()
        search_engine_client.upsert_items(dataset.actual_database_name, [item["_id"] for item in text_search_updates], text_search_updates)
