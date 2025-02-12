import logging

from data_map_backend.utils import DotDict
from data_map_backend.views.other_views import get_serialized_dataset_cached
from legacy_backend.logic.chat_and_extraction_common import _sort_fields_logically
from legacy_backend.logic.search_common import (
    get_document_details_by_id,
    get_field_similarity_threshold,
    get_relevant_parts_of_item_using_query_vector,
    get_suitable_generator,
)


def get_item_question_context(
    dataset_id: int,
    item_id: str,
    source_fields: list[str],
    question: str,
    max_characters_per_field: int | None = 5000,
    max_total_characters: int | None = None,
) -> dict:
    dataset = get_serialized_dataset_cached(dataset_id)
    required_fields = {"_id"}
    source_fields_set = set(source_fields)
    if "_descriptive_text_fields" in source_fields_set:
        required_fields = required_fields.union(dataset.schema.descriptive_text_fields)
        source_fields_set.remove("_descriptive_text_fields")
        source_fields_set.update(dataset.schema.descriptive_text_fields)
    if "_full_text_snippets" in source_fields:
        chunk_vector_field_name = dataset.merged_advanced_options.get("full_text_chunk_embeddings")
        if chunk_vector_field_name:
            chunk_vector_field = DotDict(dataset.schema.object_fields.get(chunk_vector_field_name))
            chunk_field = chunk_vector_field.source_fields[0]
            required_fields.add(chunk_field)
    required_fields.update([field for field in source_fields if not field.startswith("_")])

    full_item = get_document_details_by_id(dataset_id, item_id, tuple(required_fields), None) or {}

    text = ""
    source_fields = list(source_fields_set)
    _sort_fields_logically(source_fields)

    for source_field in source_fields:
        if source_field == "_full_text_snippets":
            continue
        elif source_field.startswith("_"):
            continue
        else:
            value = full_item.get(source_field, "n/a")
            value = str(value)[:max_characters_per_field] if max_characters_per_field else str(value)
            name = dataset.schema.object_fields.get(source_field, {}).get("name", None) or source_field
            text += f"{name}: {value}\n"
            if max_total_characters and len(text) >= max_total_characters:
                break

    max_chunks_to_show_all = 20
    max_selected_chunks = 5
    if "_full_text_snippets" in source_fields and (not max_total_characters or len(text) < max_total_characters):
        chunk_vector_field_name = dataset.merged_advanced_options.get("full_text_chunk_embeddings")
        if chunk_vector_field_name:
            chunk_vector_field = DotDict(dataset.schema.object_fields.get(chunk_vector_field_name))
            chunk_field = chunk_vector_field.source_fields[0]
            chunks = full_item.get(chunk_field, [])
            full_text = " ".join([chunk.get("text", "") for chunk in chunks])
            if len(chunks) <= max_chunks_to_show_all and (
                not max_characters_per_field or len(full_text) <= max_characters_per_field
            ):
                text += f"Full Text:\n"
                text += f"{full_text}\n"
            else:
                generator_function = get_suitable_generator(dataset, chunk_vector_field_name)
                assert generator_function is not None
                # TODO: the query vector should ideally be only generated once for all items
                query_vector = generator_function([[question]])[0]
                score_threshold = get_field_similarity_threshold(chunk_vector_field, input_is_image=False)
                result = get_relevant_parts_of_item_using_query_vector(
                    dataset,
                    item_id,
                    chunk_vector_field_name,
                    query_vector,
                    score_threshold,
                    max_selected_chunks,
                    rerank=True,
                    query=question,
                    source_texts=chunks,
                )

                include_beginning_and_end = (not max_characters_per_field or max_characters_per_field >= 5000) and len(
                    chunks
                ) > max_selected_chunks
                if include_beginning_and_end:
                    # being generous and including beginning and end of full text as those contain important information usually
                    beginning = " ".join([chunk.get("text", "") for chunk in chunks[:3]])
                    text += f"Beginning of Full Text:\n"
                    text += f"{beginning}\n\n"

                for part in result.get("_relevant_parts", []):
                    chunk_before = chunks[part.get("index") - 1].get("text", "") if part.get("index") > 0 else ""
                    this_chunk = chunks[part.get("index")].get("text", "")
                    chunk_after = (
                        chunks[part.get("index") + 1].get("text", "") if part.get("index") + 1 < len(chunks) else ""
                    )
                    relevant_text = f"[...] {chunk_before[-200:]} {this_chunk} {chunk_after[:200]} [...]"
                    if max_characters_per_field:
                        relevant_text = relevant_text[:max_characters_per_field]
                    text += f"\nPotentially Relevant Snippet from {chunk_field}:\n"
                    text += f"    {relevant_text}\n\n"
                    if max_total_characters and len(text) >= max_total_characters:
                        break

                if include_beginning_and_end:
                    end = " ".join([chunk.get("text", "") for chunk in chunks[-3:]])
                    text += f"End of Full Text:\n"
                    text += f"{end}\n\n"

    if max_total_characters and len(text) > max_total_characters:
        text = text[: max_total_characters - 1] + "\n"

    return {"context": text}
