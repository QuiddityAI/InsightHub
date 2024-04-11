import json
import logging

from utils.dotdict import DotDict
from logic.search import get_search_results, get_document_details_by_id
from logic.search_common import get_relevant_parts_of_item_using_query_vector, get_field_similarity_threshold, get_suitable_generator
from database_client.django_client import get_dataset


def get_global_question_context(search_settings: dict) -> dict:
    """ Given a natural language question, return the context that
    is relevant to answer the question using an LLM from any matching items
    in the specified dataset(s) (aka 'global').

    The question is the search query in the search_settings dict. """

    # Global question should use the top-5 hybrid search results as context.
    # The descriptive text fields (aka short text fields) should always be included as context.
    # If there is full text available, the keyword results should have the provided snippet as context
    # and the chunk vector results the (max 2) best chunks with extended context.

    search_settings["result_list_items_per_page"] = 5
    search_settings["search_algorithm"] = "hybrid"
    search_settings["max_sub_items_per_item"] = 2
    search_settings["use_bolding_in_highlights"] = False

    try:
        params_str = json.dumps({'search': search_settings}, indent=2)  # for caching
        result = get_search_results(params_str, purpose='list')
    except ValueError as e:
        logging.error(e)
        import traceback
        traceback.print_exc()
        return {'context': None, 'error': str(e.args)}  # TODO: there could be other reasons, e.g. dataset not found

    sorted_ids = result["sorted_ids"]
    items_by_dataset = result['items_by_dataset']

    context = ""
    datasets = {ds_id: get_dataset(ds_id) for ds_id in items_by_dataset.keys()}
    for ds_id, item_id in sorted_ids:
        dataset = datasets[ds_id]
        item = items_by_dataset[ds_id][item_id]
        context += _item_to_context(item, dataset) + "\n"

    return {'context': context}


def _item_to_context(item: dict, dataset: DotDict) -> str:
    always_included_fields = dataset.descriptive_text_fields
    _sort_fields_logically(always_included_fields)

    missing_fields = [field for field in always_included_fields if field not in item]

    chunk_fields_with_relevant_parts: list[str] = [part.get('field') for part in item.get("_relevant_parts", []) if part.get("index") is not None]
    missing_fields += [field for field in chunk_fields_with_relevant_parts if field not in item]

    if missing_fields:
        full_item = get_document_details_by_id(item['_dataset_id'], item['_id'], tuple(missing_fields), None) or {}
        for field in missing_fields:
            item[field] = full_item.get(field)

    context: str = f"Item: [{item['_dataset_id']}, {item['_id']}]\n"
    for field in always_included_fields:
        assert isinstance(field, str)
        if item[field] is None or item[field] == "":
            continue
        context += f"  {field}: {item[field]}\n"

    for part in item.get("_relevant_parts", []):
        if part.get("index") is None:
            if part.get("field") in always_included_fields:
                continue
            # the relevant part comes from keyword search, there is just the 'value'
            relevant_text = f"[...] {part.get('value')} [...]"
        else:
            # the relevant part comes from a chunk field
            chunks = item.get(part.get('field'), [])
            if len(chunks) <= part.get("index"):
                logging.warning(f"Chunk field {part.get('field')} has less chunks than expected.")
                continue
            chunk_before = chunks[part.get("index") - 1].get('text', '') if part.get("index") > 0 else ""
            this_chunk = chunks[part.get("index")].get('text', '')
            chunk_after = chunks[part.get("index") + 1].get('text', '') if part.get("index") < part.get('array_size', 0) else ""
            relevant_text = f"[...] {chunk_before[-200:]} {this_chunk} {chunk_after[:200]} [...]"
        context += f"  Potentially Relevant Snippet from {part.get('field')}:\n"
        context += f"    {relevant_text}\n"

    return context


def get_item_question_context(dataset_id: int, item_id: str, source_fields: list[str], question: str) -> dict:
    dataset = get_dataset(dataset_id)
    required_fields = {'_id'}
    source_fields_set = set(source_fields)
    if "_descriptive_text_fields" in source_fields_set:
        required_fields = required_fields.union(dataset.descriptive_text_fields)
        source_fields_set.remove("_descriptive_text_fields")
        source_fields_set.update(dataset.descriptive_text_fields)
    if "_full_text_snippets" in source_fields:
        chunk_vector_field_name = dataset.defaults.get("full_text_chunk_embeddings")
        if chunk_vector_field_name:
            chunk_vector_field = DotDict(dataset.object_fields.get(chunk_vector_field_name))
            chunk_field = chunk_vector_field.source_fields[0]
            required_fields.add(chunk_field)
    required_fields.update([field for field in source_fields if not field.startswith("_")])

    full_item = get_document_details_by_id(dataset_id, item_id, tuple(required_fields), None) or {}

    text = ""
    max_characters_per_field = 5000
    source_fields = list(source_fields_set)
    _sort_fields_logically(source_fields)

    for source_field in source_fields:
        if source_field == "_full_text_snippets":
            continue
        else:
            value = full_item.get(source_field, "n/a")
            value = str(value)[:max_characters_per_field]
            text += f'{source_field}: {value}\n'

    max_chunks_to_show_all = 20
    max_selected_chunks = 5
    if "_full_text_snippets" in source_fields:
        chunk_vector_field_name = dataset.defaults.get("full_text_chunk_embeddings")
        if chunk_vector_field_name:
            chunk_vector_field = DotDict(dataset.object_fields.get(chunk_vector_field_name))
            chunk_field = chunk_vector_field.source_fields[0]
            chunks = full_item.get(chunk_field, [])
            if len(chunks) <= max_chunks_to_show_all:
                full_text = " ".join([chunk.get('text', '') for chunk in chunks])
                text += f'Full Text:\n'
                text += f'{full_text}\n'
            else:
                generator_function = get_suitable_generator(dataset, chunk_vector_field_name)
                assert generator_function is not None
                query_vector = generator_function([[question]])[0]
                score_threshold = get_field_similarity_threshold(chunk_vector_field, input_is_image=False)
                result = get_relevant_parts_of_item_using_query_vector(dataset, item_id, chunk_vector_field_name, query_vector, score_threshold, max_selected_chunks)
                for part in result.get('_relevant_parts', []):
                    chunk_before = chunks[part.get("index") - 1].get('text', '') if part.get("index") > 0 else ""
                    this_chunk = chunks[part.get("index")].get('text', '')
                    chunk_after = chunks[part.get("index") + 1].get('text', '') if part.get("index") < part.get('array_size', 0) else ""
                    relevant_text = f"[...] {chunk_before[-200:]} {this_chunk} {chunk_after[:200]} [...]"
                    text += f"\nPotentially Relevant Snippet from {chunk_field}:\n"
                    text += f"    {relevant_text}\n\n"

    return {'context': text}


def _sort_fields_logically(fields: list[str]):
    # if there is 'title' or 'name' in always_included_fields, it should be the first field
    if 'title' in fields:
        fields.remove('title')
        fields.insert(0, 'title')
    if 'name' in fields:
        fields.remove('name')
        fields.insert(0, 'name')
