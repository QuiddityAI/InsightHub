import asyncio
import logging
import os
import pickle
from collections import defaultdict
import litellm
import base64
import config.embeddings as emb_config


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


def get_pubmedbert_embeddings(texts: list[str]):
    raise NotImplementedError("PubmedBERT embeddings are not supported in this version")


def get_clip_text_embeddings(texts: list[str], model_name: str | None = None) -> list[list[float]]:
    logging.warning("model_name is ignored for clip embeddings")
    embeddings = []
    for txt in texts:  # google model ony supports single text as input
        response = litellm.embedding(
            input=txt,
            **emb_config.clip_model_kwargs,  # type: ignore
        )
        embeddings.append(response.data[0]["embedding"])
    return embeddings


def get_clip_image_embeddings(image_paths: list[str], model_name: str | None = None) -> list[list[float]]:
    logging.warning("model_name is ignored for clip embeddings")

    def encode_image_to_base64(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    encoded_images = ["data:image/jpeg;base64," + encode_image_to_base64(image_path) for image_path in image_paths]

    embeddings = []
    for img in encoded_images:  # google model ony supports single image as input
        response = litellm.embedding(
            input=img,
            **emb_config.clip_model_kwargs,  # type: ignore
        )
        embeddings.append(response.data[0]["embedding"])
    return embeddings


def add_e5_prefix(texts: list[str], prefix: str, max_text_length: int = 2000):
    # e5 supports 512 tokens ~ 2000 characters
    prefix = prefix or "query:"
    # alternative: "passage: " for documents meant for retrieval
    texts = [prefix + " " + t[:max_text_length] for t in texts]
    return texts


def get_local_embeddings(texts: list[str], model_name: str) -> list[list[float]]:
    batch_size = 256
    embeddings = []
    for i in range(0, len(texts), batch_size):
        embeddings.extend(_get_local_litellm_embeddings(texts[i : i + batch_size], model_name))
    return embeddings


def get_hosted_embeddings(texts: list[str], model_name: str) -> list[list[float]]:
    batch_size = 256
    embeddings = []
    for i in range(0, len(texts), batch_size):
        embeddings.extend(_get_hosted_litellm_embeddings(texts[i : i + batch_size], model_name))
    return embeddings


def _get_local_litellm_embeddings(texts: list[str], model_name: str):
    promise = litellm.aembedding(input=texts, **emb_config.get_local_emb_litellm_kwargs(model_name))
    resp = asyncio.run(promise)
    return [d["embedding"] for d in resp["data"]]


def _get_hosted_litellm_embeddings(texts: list[str], model_name: str):
    promise = litellm.aembedding(input=texts, **emb_config.get_hosted_emb_litellm_kwargs(model_name))
    resp = asyncio.run(promise)
    return [d["embedding"] for d in resp["data"]]
