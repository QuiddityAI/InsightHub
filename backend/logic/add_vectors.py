import logging

import numpy as np

from logic.model_client import get_embedding, get_openai_embedding_batch, save_embedding_cache
from logic.gensim_w2v_vectorizer import GensimW2VVectorizer


def add_vectors_to_results(search_results, query, params, task_results=None):
    query_embedding = get_embedding(query)

    # using the code below leads to broken vectors for some reasons:
    # texts = [item.get("title", "") + " " + item.get("abstract", "") for item in results_part]
    # chunk_size = 30  # 30 -> 2.7GB GPU RAM (almost linear)
    # embeddings = np.zeros((0, 768))
    # for i in range(0, len(texts), chunk_size):
    #     embeddings = np.append(embeddings, get_embedding(texts[i:i+chunk_size]), axis=0)

    #texts = {item["DOI"]: item.get("title", "") + " " + item.get("abstract", "")[:2000] for item in results_part}
    #embeddings = get_openai_embedding_batch(texts)
    #save_embedding_cache()

    if params["vectorizer"] in ["pubmedbert", "openai"]:
        if task_results is not None:
            task_results["progress"]["total_steps"] = len(search_results)

        for i, item in enumerate(search_results):
            #item_embedding = embeddings[item["DOI"]]
            item_embedding = get_embedding(item.get("title", "") + " " + item.get("abstract", ""), item["DOI"]).tolist()
            item["vector"] = item_embedding
            item["distance"] = np.dot(query_embedding, item_embedding)

            if task_results is not None:
                task_results["progress"]["current_step"] = i

    elif params["vectorizer"] == "gensim_w2v_tf_idf":

        corpus = [item["abstract"] for item in search_results]
        vectorizer = GensimW2VVectorizer()
        vectorizer.prepare(corpus)
        query_embedding = vectorizer.get_embedding(query)

        if task_results is not None:
            task_results["progress"]["total_steps"] = len(search_results)

        for i, item in enumerate(search_results):
            item_embedding = vectorizer.get_embedding(item.get("abstract", "")).tolist()
            item["vector"] = item_embedding
            item["distance"] = np.dot(query_embedding, item_embedding)

            if task_results is not None:
                task_results["progress"]["current_step"] = i

    else:
        logging.error("vectorizer unknown: " + params["vectorizer"])

    save_embedding_cache()
