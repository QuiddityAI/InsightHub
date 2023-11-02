from collections import defaultdict
import logging
import time

from database_client.django_client import get_object_schema
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.text_search_engine_client import TextSearchEngineClient

from logic.extract_pipeline import get_pipeline_steps
from logic.insert_logic import get_index_settings
from logic.insert_logic import update_database_layout

from utils.dotdict import DotDict


def delete_field_content(schema_id: int, field_identifier: str):
    vector_db_client = VectorSearchEngineClient.get_instance()
    vector_db_client.delete_field(schema_id, field_identifier)
    search_engine_client = TextSearchEngineClient.get_instance()
    search_engine_client.delete_field(schema_id, field_identifier)


def generate_missing_values(schema_id: int, field_identifier: str):
    logging.warning(f"Generating missing values for schema {schema_id}, field {field_identifier}...")
    schema = get_object_schema(schema_id)

    # the field to be filled in might not have the necessary database columns yet:
    update_database_layout(schema_id)

    pipeline_steps, required_fields = get_pipeline_steps(schema, only_fields=[field_identifier])

    search_engine_client = TextSearchEngineClient.get_instance()
    items_processed = 0
    total_items_estimated = search_engine_client.get_all_items_with_missing_field_count(schema_id, field_identifier)
    logging.warning(f"Total items with missing value: {total_items_estimated}")

    def _process(elements):
        nonlocal items_processed
        t1 = time.time()
        changed_fields = generate_missing_values_for_given_elements(pipeline_steps, elements)
        t2 = time.time()
        generation_duration = t2 - t1
        _update_indexes_with_generated_values(schema, elements, changed_fields)
        index_update_duration = time.time() - t2
        duration = generation_duration + index_update_duration
        items_processed += len(elements)
        logging.warning(f"Processed {items_processed} of {total_items_estimated} ({(items_processed / float(total_items_estimated)) * 100:.1f} %)")
        logging.warning(f"Time per item: generation {generation_duration / len(elements) * 1000:.2f} ms, index update {index_update_duration / len(elements) * 1000:.2f} ms, total {duration / len(elements) * 1000:.2f} ms")
        logging.warning(f"Estimated remaining time: {(duration / len(elements) * (total_items_estimated - items_processed)) / 60.0:.1f} min")

    batch_size = 512
    generator = search_engine_client.get_all_items_with_missing_field(schema_id, field_identifier, required_fields, internal_batch_size=batch_size)
    elements = []
    last_batch_time = time.time()
    for element in generator:
        elements.append(element)
        if len(elements) % batch_size == 0:
            element_retrieval_time = time.time() - last_batch_time
            logging.warning(f"Time to retrieve {len(elements)} items: {element_retrieval_time * 1000:.2f} ms")
            _process(elements)
            elements = []
            last_batch_time = time.time()
    if elements:
        # process remaining elements
        element_retrieval_time = time.time() - last_batch_time
        logging.warning(f"Time to retrieve {len(elements)} items: {element_retrieval_time * 1000:.2f} ms")
        _process(elements)
    logging.warning(f"Done")


def generate_missing_values_for_given_elements(pipeline_steps: list[list[dict]], elements: list[dict]):
    changed_fields = defaultdict(list)
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

                element_indexes.append(i)
                source_data = []
                for source_field in pipeline_step.source_fields:
                    if source_field in element:
                        source_data.append(element[source_field])
                source_data_total.append(source_data)

            results = pipeline_step.generator_function(source_data_total)

            for element_index, result in zip(element_indexes, results):
                elements[element_index][pipeline_step.target_field] = result
                changed_fields[element_index].append(pipeline_step.target_field)
    return changed_fields  # elements is changed in-place


def _update_indexes_with_generated_values(schema, elements, changed_fields):
    index_settings = get_index_settings(schema)

    vector_db_client = VectorSearchEngineClient.get_instance()

    for vector_field in index_settings.indexed_vector_fields:
        ids = []
        vectors = []
        payloads = []
        for element_index, element in enumerate(elements):
            if vector_field not in changed_fields[element_index]:
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
            vector_db_client.upsert_items(schema.id, vector_field, ids, payloads, vectors)

    # add it to the textsearch storage as the last step because if the process is interrupted, this is the ground of truth
    search_engine_client = TextSearchEngineClient.get_instance()
    # TODO: exclude vectors that are stored in vector DB (what if that setting changes?)
    search_engine_client.upsert_items(schema.id, [item["_id"] for item in elements], elements)
