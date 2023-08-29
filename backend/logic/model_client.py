from collections import defaultdict
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
    return get_pubmedbert_embedding(text, text_id)


def get_pubmedbert_embedding(text: str, text_id: str = None):

    config_name = embedding_model + embedding_strategy
    if text_id and text_id in embedding_cache[config_name]:
        return embedding_cache[config_name][text_id]

    url = 'http://localhost:55180/api/embedding'
    data = {
        'text': text,
        'model': embedding_model,
        'embedding_strategy': embedding_strategy,
    }
    result = requests.post(url, json=data)
    embedding = np.asarray(result.json()["embedding"])[0]  # for now, no support for batches

    if text_id:
        embedding_cache[config_name][text_id] = embedding
    return embedding


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
