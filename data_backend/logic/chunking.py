from typing import Iterable


def chunk_text_generator(source_fields_list_batch: Iterable[Iterable[str | Iterable[str]]], chunk_size_in_characters: int, overlap_in_characters: int) -> list[str]:
    batch_result = []
    for source_fields_list in source_fields_list_batch:
        item_result = []
        for source_data in source_fields_list:
            if isinstance(source_data, str):
                chunked_text = chunk_text(source_data, chunk_size_in_characters, overlap_in_characters)
                item_result = chunked_text
            elif isinstance(source_data, Iterable):
                for text in source_data:
                    chunked_text = chunk_text(text, chunk_size_in_characters, overlap_in_characters)
                    item_result.append(chunked_text)
        batch_result.append(item_result)
    return batch_result


def chunk_text(text: str, chunk_size_in_characters: int, overlap_in_characters: int):
    chunks = []
    for i in range(0, len(text), chunk_size_in_characters - overlap_in_characters):
        chunks.append(text[i:i + chunk_size_in_characters])
    return chunks