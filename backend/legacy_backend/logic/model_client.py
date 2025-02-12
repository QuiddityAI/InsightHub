import logging
import os
import pickle
from collections import defaultdict

import numpy as np
import requests

embedding_model = "BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
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


def get_embedding(text: str, text_id: str = "") -> np.ndarray:
    return get_pubmedbert_embeddings([text])[0]


def get_pubmedbert_embeddings(texts: list[str]):
    url = os.getenv("model_server_host", "http://localhost:55180") + "/api/embedding/bert"
    data = {
        "texts": texts,
        "model_name": embedding_model,
        "embedding_strategy": embedding_strategy,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


def get_sentence_transformer_embeddings(texts: list[str], model_name: str, prefix: str):
    url = os.getenv("model_server_host", "http://localhost:55180") + "/api/embedding/sentence_transformer"
    data = {
        "texts": texts,
        "model_name": model_name,
        "prefix": prefix,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


def get_clip_text_embeddings(texts: list[str], model_name: str):
    url = os.getenv("model_server_host", "http://localhost:55180") + "/api/embedding/clip/text"
    data = {
        "texts": texts,
        "model_name": model_name,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


def get_clip_image_embeddings(image_paths: list[str], model_name: str):
    url = os.getenv("model_server_host", "http://localhost:55180") + "/api/embedding/clip/image"
    data = {
        "image_paths": image_paths,
        "model_name": model_name,
    }
    result = requests.post(url, json=data)
    embeddings = np.asarray(result.json()["embeddings"])
    return embeddings


def add_e5_prefix(texts: list[str], prefix: str, max_text_length: int = 1000):
    prefix = prefix or "query:"
    # alternative: "passage: " for documents meant for retrieval
    texts = [prefix + " " + t[:max_text_length] for t in texts]
    return texts


def get_infinity_embeddings(texts: list[str], model_name: str):
    batch_size = 256
    embeddings = []
    for i in range(0, len(texts), batch_size):
        embeddings.extend(_get_infinity_embeddings(texts[i : i + batch_size], model_name))
    return embeddings


def _get_infinity_embeddings(texts: list[str], model_name: str):
    url = os.getenv("infinity_server_host", "http://infinity-model-server:55181") + "/embeddings"
    data = {"input": texts, "model": model_name}
    result = requests.post(url, json=data)
    try:
        embeddings = np.asarray([x["embedding"] for x in result.json()["data"]])
    except KeyError:
        logging.error("Batch of embeddings lost because at least one could not be processed by Infinity")
        logging.error(result.json())
        return [np.zeros(768) for _ in range(len(texts))]
    return embeddings
