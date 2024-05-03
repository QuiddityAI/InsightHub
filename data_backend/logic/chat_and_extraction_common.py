import json
import logging

from utils.dotdict import DotDict
from logic.search_common import get_document_details_by_id
from database_client.django_client import get_dataset


def get_context_for_each_item_in_search_results(sorted_ids: list[tuple[int, str]], items_by_dataset,
                                                reranked_chunks: int=0, question: str | None=None) -> list[str]:
    contexts = []
    datasets = {ds_id: get_dataset(ds_id) for ds_id in items_by_dataset.keys()}
    for ds_id, item_id in sorted_ids:
        dataset = datasets[ds_id]
        item = items_by_dataset[ds_id][item_id]
        contexts.append(_item_to_context(item, dataset, reranked_chunks, question))
    return contexts


def _item_to_context(item: dict, dataset: DotDict, reranked_chunks: int=0, question: str | None=None) -> str:
    always_included_fields = dataset.descriptive_text_fields
    _sort_fields_logically(always_included_fields)

    missing_fields = [field for field in always_included_fields if field not in item]

    chunk_fields_with_relevant_parts: list[str] = [part.get('field') for part in item.get("_relevant_parts", []) if part.get("index") is not None]
    missing_fields += [field for field in chunk_fields_with_relevant_parts if field not in item]

    if question and reranked_chunks > 0:
        # oversample chunks and rerank:
        chunk_vector_field_name = dataset.defaults.get("full_text_chunk_embeddings")
        chunk_source_field = dataset.object_fields[chunk_vector_field_name].source_fields[0] if dataset.object_fields[chunk_vector_field_name].source_fields else None
        missing_fields += [chunk_source_field]
        missing_fields = tuple(set(missing_fields))
        relevant_parts_json = json.dumps(item.get("_relevant_parts", []))
        full_item = get_document_details_by_id(
            item['_dataset_id'], item['_id'], missing_fields, relevant_parts_json,
            top_n_full_text_chunks=reranked_chunks, query=question) or {}
        item["_relevant_parts"] = full_item['_relevant_parts']
        for field in missing_fields:
            item[field] = full_item.get(field)
    elif missing_fields:
        # just get missing fields:
        missing_fields = tuple(set(missing_fields))
        full_item = get_document_details_by_id(
            item['_dataset_id'], item['_id'], missing_fields) or {}
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
            chunk_after = chunks[part.get("index") + 1].get('text', '') if part.get("index") + 1 < len(chunks) else ""
            relevant_text = f"[...] {chunk_before[-200:]} {this_chunk} {chunk_after[:200]} [...]"
        context += f"  Potentially Relevant Snippet from {part.get('field')}:\n"
        context += f"    {relevant_text}\n"

    return context


def _sort_fields_logically(fields: list[str]):
    # if there is 'title' or 'name' in always_included_fields, it should be the first field
    if 'title' in fields:
        fields.remove('title')
        fields.insert(0, 'title')
    if 'name' in fields:
        fields.remove('name')
        fields.insert(0, 'name')