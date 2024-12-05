import logging
from typing import Callable
import json
import os

import openai

from data_map_backend.utils import DotDict
from ..utils.helpers import join_extracted_text_sources

from ..logic.model_client import get_pubmedbert_embeddings, get_sentence_transformer_embeddings, get_clip_text_embeddings, get_clip_image_embeddings, get_infinity_embeddings, add_e5_prefix
from ..logic.chunking import chunk_text_generator

from ..api_clients import deepinfra_client

from ingest.logic.office_documents import ai_file_processing_generator


GPU_IS_AVAILABLE = os.getenv('GPU_IS_AVAILABLE', "False") == "True"


def get_generator_function_from_field(field: DotDict, always_return_single_value_per_item: bool = False) -> Callable:
    parameters = field.generator.default_parameters or {}
    if field.generator_parameters:
        parameters.update(field.generator_parameters)
    module = field.generator.module
    return get_generator_function(module, parameters, field.is_array and not always_return_single_value_per_item)


def get_generator_function(module: str, parameters: dict, target_field_is_array: bool) -> Callable:
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
    if module == 'pubmedbert':
        generator = lambda batch, log_error=default_log: get_pubmedbert_embeddings([join_extracted_text_sources(source_fields_list) for source_fields_list in batch])
    elif module == 'open_ai_text_embedding_ada_002':
        generator = lambda batch, log_error=default_log: get_openai_embedding_batch([join_extracted_text_sources(t) for t in batch])
    elif module == 'sentence_transformer':
        if parameters.model_name == 'intfloat/e5-base-v2':
            def generator_fn(batch, log_error=default_log):
                preprocessed_texts = [join_extracted_text_sources(t) for t in batch]
                preprocessed_texts = add_e5_prefix(preprocessed_texts, parameters.prefix)
                if GPU_IS_AVAILABLE or len(batch) == 1:
                    return get_infinity_embeddings(preprocessed_texts, parameters.model_name)
                return deepinfra_client.get_embeddings(preprocessed_texts, parameters.model_name)
            generator = generator_fn
        else:
            generator = lambda batch, log_error=default_log: get_sentence_transformer_embeddings([join_extracted_text_sources(t) for t in batch], parameters.model_name, parameters.prefix)
    elif module == 'clip_text':
        generator = lambda batch, log_error=default_log: get_clip_text_embeddings([join_extracted_text_sources(t) for t in batch], parameters.model_name)
    elif module == 'clip_image':
        generator = lambda batch, log_error=default_log: get_clip_image_embeddings([field for source_fields in batch for field in source_fields], parameters.model_name)
    elif module == 'favicon_url':
        generator = lambda batch, log_error=default_log: [get_favicon_url(urls[0]) for urls in batch if urls]
    elif module == 'chunking':
        generator = lambda batch, log_error=default_log: chunk_text_generator(batch, parameters.chunk_size_in_characters, parameters.overlap_in_characters)
    elif module == 'ai_file_processing':
        generator = lambda batch, log_error=default_log: ai_file_processing_generator(batch, log_error, parameters)

    if not generator:
        logging.error(f"Generator module {module} not found")
        return lambda x, log_error=default_log: None

    if target_field_is_array:
        generate_one_value_for_each_item = generator

        def generate_value_for_each_element_in_array_field(batch, log_error=default_log):
            # e.g. if there is a batch of 50 items and each item has one source field with 10 values
            # we flatten the batch to a list of 500 values
            flattened_batch = [[element] for source_fields in batch for array_field in source_fields for element in array_field or [None]]
            # then we generate a value for each of the 500 values
            flattened_results = generate_one_value_for_each_item(flattened_batch, log_error)
            restructured_results = []
            # and then we restructure the results back to the original batch structure
            for item in batch:
                original_element_count = len([element for array_field in item for element in array_field or [None]])
                restructured_results.append(flattened_results[:original_element_count])
                flattened_results = flattened_results[original_element_count:]
            return restructured_results

        return generate_value_for_each_element_in_array_field
    else:
        return generator



with open("../openai_credentials.json", "rb") as f:
    openai_credentials = json.load(f)
openai.api_key = openai_credentials["secret_key"]


def get_openai_embedding_batch(texts: list[str]):
    openai_model = "text-embedding-ada-002"
    results = []

    chunk_size = 35  # 2000 / 60 requests per minute (limit for first 48h)
    for i in range(0, len(texts), chunk_size):
        result: dict = openai.Embedding.create(  # type: ignore
            model=openai_model,
            input=texts[i:i+chunk_size],
        ) # type: ignore
        # roughly 1500 characters per abstract and 260 tokens per abstract
        # -> 0.1ct per 10k tokens -> 0.1ct per 30 abstracts
        # -> 5.2 ct per 2k abstracts (one search)
        # -> 60M abstracts would be 1560€
        for result_item in result["data"]:
            results.append(result_item["embedding"])

    return results


def get_favicon_url(url):
    domain = url.split("/")[2]
    return f"https://www.google.com/s2/favicons?sz=64&domain={domain}"
    domain = url.split("/")[2]
    protocol = url.split("/")[0]
    return f"{protocol}//{domain}/favicon.ico"
