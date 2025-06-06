import logging
import os
from typing import Callable, Literal

import litellm

from data_map_backend.utils import DotDict
from ingest.logic.office_documents import ai_file_processing_generator
from ingest.logic.scientific_articles import scientific_article_processing_generator
from ingest.logic.tenders import tender_enrichment_generator
from legacy_backend.logic.chunking import chunk_text_generator
from legacy_backend.logic.model_client import (
    add_e5_prefix,
    get_clip_image_embeddings,
    get_clip_text_embeddings,
    get_hosted_embeddings,
    get_local_embeddings,
)
from legacy_backend.utils.helpers import join_extracted_text_sources

GPU_IS_AVAILABLE = os.getenv("GPU_IS_AVAILABLE", "False") == "True"


def get_generator_function_from_field(
    field: DotDict, always_return_single_value_per_item: bool = False, mode: Literal["ingest", "search"] = "ingest"
) -> Callable:
    parameters = field.generator.default_parameters or {}
    if field.generator_parameters:
        parameters.update(field.generator_parameters)
    module = field.generator.module
    return get_generator_function(
        module, parameters, field.is_array and not always_return_single_value_per_item, mode=mode
    )


def get_generator_function(
    module: str, parameters: dict, target_field_is_array: bool, mode: Literal["ingest", "search"] = "ingest"
) -> Callable:
    # the input to the generators is a list ('batch') of source_fields for each item in the batch
    # source_fields is itself again a list of the data in the source fields assigned to this generated field
    # and the data can then be either a simple data type like str, url or int, or a list of such data
    #
    # i.e. if just one simple text field is assigned as a source field and there is one item in the batch, the input is [ [ "text" ] ]
    # if one array field is assigned as a source field and one item in the batch, the input is [ [ ["text1", "text2"] ] ]
    # if one array and one simple field is assigned as source fields, the input is [ [ ["text1", "text2"], "text3" ] ]
    # the same applies to non-text fields, just with e.g. image paths instead of text
    parameters = DotDict(parameters)
    generator: Callable | None = None
    default_log = logging.warning

    # migrated to litellm
    def open_ai_text_embedding_ada_002_generator(batch, log_error=default_log):
        return get_openai_embedding_batch([join_extracted_text_sources(t) for t in batch])

    # migrated to litellm
    def sentence_transformer_generator(batch, log_error=default_log):
        prefix = parameters.get("prefix" if mode == "ingest" else "query_prefix", "")
        if mode not in ["ingest", "search"]:
            logging.warning(f"Unknown prefix mode {mode}")
        if GPU_IS_AVAILABLE or len(batch) == 1:
            return get_local_embeddings(
                add_e5_prefix([join_extracted_text_sources(t) for t in batch], prefix),
                parameters.model_name,
            )
        else:
            return get_hosted_embeddings(
                add_e5_prefix([join_extracted_text_sources(t) for t in batch], prefix), parameters.model_name
            )

    def clip_text_generator(batch, log_error=default_log):
        return get_clip_text_embeddings([join_extracted_text_sources(t) for t in batch], parameters.model_name)

    def clip_image_generator(batch, log_error=default_log):
        return get_clip_image_embeddings(
            [field for source_fields in batch for field in source_fields], parameters.model_name
        )

    def favicon_url_generator(batch, log_error=default_log):
        return [get_favicon_url(urls[0]) for urls in batch if urls]

    def chunking_generator(batch, log_error=default_log):
        return chunk_text_generator(batch, parameters.chunk_size_in_characters, parameters.overlap_in_characters)

    def ai_file_processing_generator_func(batch, log_error=default_log):
        return ai_file_processing_generator(batch, log_error, parameters)

    def scientific_article_processing_func(batch, log_error=default_log):
        return scientific_article_processing_generator(batch, log_error, parameters)

    def tender_enrichment_generator_func(batch, log_error=default_log):
        return tender_enrichment_generator(batch, log_error, parameters)

    generator_mapping = {
        "open_ai_text_embedding_ada_002": open_ai_text_embedding_ada_002_generator,
        "sentence_transformer": sentence_transformer_generator,
        "clip_text": clip_text_generator,
        "clip_image": clip_image_generator,
        "favicon_url": favicon_url_generator,
        "chunking": chunking_generator,
        "ai_file_processing": ai_file_processing_generator_func,
        "tender_enrichment": tender_enrichment_generator_func,
        "scientific_article_processing": scientific_article_processing_func,
    }

    generator = generator_mapping.get(module)

    if not generator:
        logging.error(f"Generator module {module} not found")
        return lambda x, log_error=default_log: None

    if target_field_is_array:
        generate_one_value_for_each_item = generator

        def generate_value_for_each_element_in_array_field(batch, log_error=default_log):
            # e.g. if there is a batch of 50 items and each item has one source field with 10 values
            # we flatten the batch to a list of 500 values
            flattened_batch = [
                [element] for source_fields in batch for array_field in source_fields for element in array_field or []
            ]
            # then we generate a value for each of the 500 values
            flattened_results = generate_one_value_for_each_item(flattened_batch, log_error)
            restructured_results = []
            # and then we restructure the results back to the original batch structure
            for item in batch:
                original_element_count = len([element for array_field in item for element in array_field or []])
                restructured_results.append(flattened_results[:original_element_count])
                flattened_results = flattened_results[original_element_count:]
            return restructured_results

        return generate_value_for_each_element_in_array_field
    else:
        return generator


def get_openai_embedding_batch(texts: list[str]):
    results = []

    chunk_size = 35  # 2000 / 60 requests per minute (limit for first 48h)
    for i in range(0, len(texts), chunk_size):
        resp = litellm.embedding(
            model="openai/text-embedding-ada-002",
            input=texts[i : i + chunk_size],
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # roughly 1500 characters per abstract and 260 tokens per abstract
        # -> 0.1ct per 10k tokens -> 0.1ct per 30 abstracts
        # -> 5.2 ct per 2k abstracts (one search)
        # -> 60M abstracts would be 1560€
        for result_item in resp["data"]:
            results.append(result_item["embedding"])

    return results


def get_favicon_url(url):
    domain = url.split("/")[2]
    return f"https://www.google.com/s2/favicons?sz=64&domain={domain}"
    domain = url.split("/")[2]
    protocol = url.split("/")[0]
    return f"{protocol}//{domain}/favicon.ico"
