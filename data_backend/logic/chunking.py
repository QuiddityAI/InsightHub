from typing import Iterable


def chunk_text_generator(data_from_source_fields: Iterable[str | Iterable[str]], chunk_size_in_characters: int, overlap_in_characters: int) -> list[str]:
    result = []
    for source_data in data_from_source_fields:
        if isinstance(source_data, str):
            chunked_text = chunk_text(source_data, chunk_size_in_characters, overlap_in_characters)
            result.append(chunked_text)
        elif isinstance(source_data, Iterable):
            for text in source_data:
                chunked_text = chunk_text(text, chunk_size_in_characters, overlap_in_characters)
                result.append(chunked_text)
    return result


def chunk_text(text: str, chunk_size_in_characters: int, overlap_in_characters: int):
    chunks = []
    for i in range(0, len(text), chunk_size_in_characters - overlap_in_characters):
        chunks.append(text[i:i + chunk_size_in_characters])
    return chunks