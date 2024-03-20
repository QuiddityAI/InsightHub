from typing import Callable
import json

import openai

from utils.dotdict import DotDict
from utils.helpers import join_extracted_text_sources

from logic.model_client import get_pubmedbert_embeddings, get_sentence_transformer_embeddings, get_clip_text_embeddings, get_clip_image_embeddings, get_infinity_embeddings
from logic.chunking import chunk_text_generator


def get_generator_function_from_field(field: DotDict) -> Callable:
    parameters = field.generator.default_parameters or {}
    if field.generator_parameters:
        parameters.update(field.generator_parameters)
    module = field.generator.module
    return get_generator_function(module, parameters)


def get_generator_function(module: str, parameters: dict) -> Callable:
    # the input to the generators is a list of data for each source field, and the data can be an array itself if the source field is an array field
    # i.e. if just one simple text field is assigned as a source field, the input is [ "text", ]
    # if one array field is assigned as a source field, the input is [ ["text1", "text2"], ]
    # if one array and one simple field is assigned as source fields, the input is [ ["text1", "text2"], "text3" ]
    # the same applies to non-text fields, just with e.g. image paths instead of text
    parameters = DotDict(parameters)
    if module == 'pubmedbert':
        return lambda texts: get_pubmedbert_embeddings([join_extracted_text_sources(t) for t in texts])
    elif module == 'open_ai_text_embedding_ada_002':
        return lambda texts: get_openai_embedding_batch([join_extracted_text_sources(t) for t in texts])
    elif module == 'sentence_transformer':
        if parameters.model_name == 'intfloat/e5-base-v2':
            return lambda texts: get_infinity_embeddings([join_extracted_text_sources(t) for t in texts], parameters.model_name, parameters.prefix)
        return lambda texts: get_sentence_transformer_embeddings([join_extracted_text_sources(t) for t in texts], parameters.model_name, parameters.prefix)
    elif module == 'clip_text':
        return lambda texts: get_clip_text_embeddings([join_extracted_text_sources(t) for t in texts], parameters.model_name)
    elif module == 'clip_image':
        return lambda image_paths: get_clip_image_embeddings([item for sublist in image_paths for item in sublist], parameters.model_name)
    elif module == 'favicon_url':
        return lambda source_data_list: [get_favicon_url(urls[0]) for urls in source_data_list if urls]
    elif module == 'chunking':
        return lambda source_data_list: chunk_text_generator(source_data_list, parameters.chunk_size_in_characters, parameters.overlap_in_characters)

    return lambda x: None


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
