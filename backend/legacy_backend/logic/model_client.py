from collections import defaultdict
import logging
import pickle
import os
import json

import requests
import numpy as np
import openai
from tqdm import tqdm


embedding_model = "BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
#embedding_model = "openai"
embedding_strategy = "sep_token"
embedding_cache_path = "embedding_cache.pkl"


if os.path.exists(embedding_cache_path):
    with open(embedding_cache_path, "rb") as f:
        embedding_cache = pickle.load(f)
else:
    embedding_cache = defaultdict(dict().copy)


def save_embedding_cache():
    with open(embedding_cache_path, "wb") as f:
        pickle.dump(embedding_cache, f)


def get_embedding(text: str, text_id: str = None) -> np.ndarray:
    if embedding_model == "openai":
        return get_openai_embedding(text, text_id)
    return get_pubmedbert_embeddings([text])[0]


def get_pubmedbert_embeddings(texts: list[str]):
    url =  os.getenv('model_server_host', 'http://localhost:55180') + '/api/embedding/bert'
    data = {
        'texts': texts,
        'model_name': embedding_model,
        'embedding_strategy': embedding_strategy,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


def get_sentence_transformer_embeddings(texts: list[str], model_name: str, prefix: str):
    url =  os.getenv('model_server_host', 'http://localhost:55180') + '/api/embedding/sentence_transformer'
    data = {
        'texts': texts,
        'model_name': model_name,
        'prefix': prefix,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


def get_clip_text_embeddings(texts: list[str], model_name: str):
    url =  os.getenv('model_server_host', 'http://localhost:55180') + '/api/embedding/clip/text'
    data = {
        'texts': texts,
        'model_name': model_name,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


def get_clip_image_embeddings(image_paths: list[str], model_name: str):
    url =  os.getenv('model_server_host', 'http://localhost:55180') + '/api/embedding/clip/image'
    data = {
        'image_paths': image_paths,
        'model_name': model_name,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


# ------------------- OpenAI -------------------------


with open("../openai_credentials.json", "rb") as f:
    openai_credentials = json.load(f)


openai.api_key = openai_credentials["secret_key"]
openai_model = "text-embedding-ada-002"


def get_openai_embedding(text: str, text_id: str = None):
    config_name = "openai_" + openai_model
    if text_id and text_id in embedding_cache[config_name]:
        return embedding_cache[config_name][text_id]

    result = openai.Embedding.create(
        model=openai_model,
        input=text,
    )
    embedding = result["data"][0]["embedding"]

    if text_id:
        embedding_cache[config_name][text_id] = embedding

    return embedding


def get_openai_embedding_batch(texts: dict):
    config_name = "openai_" + openai_model
    missing_embeddings_texts = []
    missing_embeddings_ids = []
    results = {}

    for text_id, text in texts.items():
        if text_id in embedding_cache[config_name]:
            results[text_id] = embedding_cache[config_name][text_id]
        else:
            missing_embeddings_texts.append(text)
            missing_embeddings_ids.append(text_id)

    if missing_embeddings_texts:

        chunk_size = 35  # 2000 / 60 requests per minute (limit for first 48h)
        for i in tqdm(range(0, len(missing_embeddings_texts), chunk_size)):
            result = openai.Embedding.create(
                model=openai_model,
                input=missing_embeddings_texts[i:i+chunk_size],
            )
            print(f"tokens: {result['usage']}, {len(missing_embeddings_texts[i:i+chunk_size])}, {len(''.join(missing_embeddings_texts[i:i+chunk_size])) / chunk_size}")
            # roughly 1500 characters per abstract and 260 tokens per abstract
            # -> 0.1ct per 10k tokens -> 0.1ct per 30 abstracts
            # -> 5.2 ct per 2k abstracts (one search)
            # -> 60M abstracts would be 1560€
            for j, result_item in enumerate(result["data"]):
                embedding = result_item["embedding"]
                text_id = missing_embeddings_ids[i+j]
                embedding_cache[config_name][text_id] = embedding

                results[text_id] = embedding

    return results


def add_e5_prefix(texts: list[str], prefix: str, max_text_length: int = 1000):
    prefix = prefix or "query:"
    # alternative: "passage: " for documents meant for retrieval
    texts = [prefix + " " + t[:max_text_length] for t in texts]
    return texts


def get_infinity_embeddings(texts: list[str], model_name: str):
    batch_size = 256
    embeddings = []
    for i in range(0, len(texts), batch_size):
        embeddings.extend(_get_infinity_embeddings(texts[i:i+batch_size], model_name))
    return embeddings


def _get_infinity_embeddings(texts: list[str], model_name: str):
    url = os.getenv('infinity_server_host', 'http://infinity-model-server:55181') + '/embeddings'
    data = {
        "input": texts,
        "model": model_name
    }
    result = requests.post(url, json=data)
    try:
        embeddings = np.asarray([x["embedding"] for x in result.json()["data"]])
    except KeyError:
        logging.error("Batch of embeddings lost because at least one could not be processed by Infinity")
        logging.error(result.json())
        return [np.zeros(768) for _ in range(len(texts))]
    return embeddings
