from collections import defaultdict
import pickle
import os

import requests
import numpy as np


embedding_model = "BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
embedding_strategy = "sep_token"
embedding_cache_path = "embedding_cache.pkl"


if os.path.exists(embedding_cache_path):
    with open(embedding_cache_path, "rb") as f:
        embedding_cache = pickle.load(f)
else:
    embedding_cache = defaultdict(dict().copy)


def get_embedding(text: str, text_id: str = None) -> np.ndarray:
    if text_id and text_id in embedding_cache[embedding_model + embedding_strategy]:
        return embedding_cache[embedding_model + embedding_strategy][text_id]

    url = 'http://localhost:55180/api/embedding'
    data = {
        'text': text,
        'model': embedding_model,
        'embedding_strategy': embedding_strategy,
    }
    result = requests.post(url, json=data)
    embedding = np.asarray(result.json()["embedding"])[0]  # for now, no support for batches

    if text_id:
        embedding_cache[embedding_model + embedding_strategy][text_id] = embedding
    return embedding


def save_embedding_cache():
    with open(embedding_cache_path, "wb") as f:
        pickle.dump(embedding_cache, f)
