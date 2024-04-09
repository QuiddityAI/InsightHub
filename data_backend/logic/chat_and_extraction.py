import json
import logging

from utils.dotdict import DotDict
from logic.search import get_search_results, get_document_details_by_id
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
    # if there is 'title' or 'name' in always_included_fields, it should be the first field
    if 'title' in always_included_fields:
        always_included_fields.remove('title')
        always_included_fields.insert(0, 'title')
    if 'name' in always_included_fields:
        always_included_fields.remove('name')
        always_included_fields.insert(0, 'name')

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
            chunk_before = item.get(part.get("field"), [])[part.get("index") - 1].get('text', '') if part.get("index") > 0 else ""
            this_chunk = item.get(part.get("field"), [])[part.get("index")].get('text', '')
            chunk_after = item.get(part.get("field"), [])[part.get("index") + 1].get('text', '') if part.get("index") < part.get('array_size', 0) else ""
            relevant_text = f"[...] {chunk_before[-200:]} {this_chunk} {chunk_after[:200]} [...]"
        context += f"  Potentially Relevant Snippet from {part.get('field')}:\n"
        context += f"    {relevant_text}\n"

    return context
