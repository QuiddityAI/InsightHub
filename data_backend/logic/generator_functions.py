from typing import Callable
import json

import openai

from utils.dotdict import DotDict

from logic.model_client import get_pubmedbert_embeddings, get_sentence_transformer_embeddings, get_clip_text_embeddings, get_clip_image_embeddings


def get_generator_function(identifier, parameters: dict) -> Callable:
    parameters = DotDict(parameters)
    if identifier == 'pubmedbert':
        return lambda texts: get_pubmedbert_embeddings([" ".join(t) for t in texts])
    elif identifier == 'open_ai_text_embedding_ada_002':
        return lambda texts: get_openai_embedding_batch([" ".join(t) for t in texts])
    elif identifier == 'sentence_transformer':
        return lambda texts: get_sentence_transformer_embeddings([" ".join(t) for t in texts], parameters.model_name, parameters.prefix)
    elif identifier == 'clip_text':
        return lambda texts: get_clip_text_embeddings([" ".join(t) for t in texts], parameters.model_name)
    elif identifier == 'clip_image':
        return lambda image_paths: get_clip_image_embeddings([x for t in image_paths for x in t], parameters.model_name)

    return lambda x: None


with open("../openai_credentials.json", "rb") as f:
    openai_credentials = json.load(f)
openai.api_key = openai_credentials["secret_key"]


def get_openai_embedding_batch(texts: list[str]):
    openai_model = "text-embedding-ada-002"
    results = []

    chunk_size = 35  # 2000 / 60 requests per minute (limit for first 48h)
    for i in range(0, len(texts), chunk_size):
        result: dict = openai.Embedding.create(
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
