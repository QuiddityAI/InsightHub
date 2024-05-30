import json
import logging

from api_clients.cohere_reranking import get_reranking_results
from utils.dotdict import DotDict
from logic.search import get_search_results
from logic.search_common import get_relevant_parts_of_item_using_query_vector, get_field_similarity_threshold, get_suitable_generator, get_document_details_by_id
from logic.chat_and_extraction_common import get_context_for_each_item_in_search_results, _sort_fields_logically
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

    num_results_in_context = 5
    item_rerank = True
    chunk_rerank = True
    oversample_for_reranking = 3 if item_rerank else 0
    search_settings["result_list_items_per_page"] = num_results_in_context + oversample_for_reranking
    search_settings["search_algorithm"] = "hybrid"
    search_settings["max_sub_items_per_item"] = 2
    search_settings["return_highlights"] = True
    search_settings["use_bolding_in_highlights"] = False
    search_settings["auto_relax_query"] = True

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

    question = search_settings.get('all_field_query', '')
    contexts = get_context_for_each_item_in_search_results(sorted_ids, items_by_dataset,
                                                           reranked_chunks=2 if chunk_rerank else 0, question=question)
    if item_rerank:
        reranking = get_reranking_results(question, tuple(contexts), num_results_in_context)
        contexts = [contexts[reranking_result.index] for reranking_result in reranking.results]
    context = "\n".join(contexts)

    return {'context': context}


def get_item_question_context(dataset_id: int, item_id: str, source_fields: list[str], question: str) -> dict:
    dataset = get_dataset(dataset_id)
    required_fields = {'_id'}
    source_fields_set = set(source_fields)
    if "_descriptive_text_fields" in source_fields_set:
        required_fields = required_fields.union(dataset.schema.descriptive_text_fields)
        source_fields_set.remove("_descriptive_text_fields")
        source_fields_set.update(dataset.schema.descriptive_text_fields)
    if "_full_text_snippets" in source_fields:
        chunk_vector_field_name = dataset.schema.advanced_options.get("full_text_chunk_embeddings")
        if chunk_vector_field_name:
            chunk_vector_field = DotDict(dataset.schema.object_fields.get(chunk_vector_field_name))
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
        elif source_field.startswith("_"):
            continue
        else:
            value = full_item.get(source_field, "n/a")
            value = str(value)[:max_characters_per_field]
            name = dataset.schema.object_fields.get(source_field, {}).get('name', None) or source_field
            text += f'{name}: {value}\n'

    max_chunks_to_show_all = 20
    max_selected_chunks = 5
    if "_full_text_snippets" in source_fields:
        chunk_vector_field_name = dataset.schema.advanced_options.get("full_text_chunk_embeddings")
        if chunk_vector_field_name:
            chunk_vector_field = DotDict(dataset.schema.object_fields.get(chunk_vector_field_name))
            chunk_field = chunk_vector_field.source_fields[0]
            chunks = full_item.get(chunk_field, [])
            if len(chunks) <= max_chunks_to_show_all:
                full_text = " ".join([chunk.get('text', '') for chunk in chunks])
                text += f'Full Text:\n'
                text += f'{full_text}\n'
            else:
                generator_function = get_suitable_generator(dataset, chunk_vector_field_name)
                assert generator_function is not None
                # TODO: the query vector should ideally be only generated once for all items
                query_vector = generator_function([[question]])[0]
                score_threshold = get_field_similarity_threshold(chunk_vector_field, input_is_image=False)
                result = get_relevant_parts_of_item_using_query_vector(
                    dataset, item_id, chunk_vector_field_name, query_vector, score_threshold,
                    max_selected_chunks, rerank=True, query=question, source_texts=chunks)
                for part in result.get('_relevant_parts', []):
                    chunk_before = chunks[part.get("index") - 1].get('text', '') if part.get("index") > 0 else ""
                    this_chunk = chunks[part.get("index")].get('text', '')
                    chunk_after = chunks[part.get("index") + 1].get('text', '') if part.get("index") + 1 < len(chunks) else ""
                    relevant_text = f"[...] {chunk_before[-200:]} {this_chunk} {chunk_after[:200]} [...]"
                    text += f"\nPotentially Relevant Snippet from {chunk_field}:\n"
                    text += f"    {relevant_text}\n\n"

    return {'context': text}
