import logging

import numpy as np

from utils.dotdict import DotDict

from logic.model_client import get_embedding, get_openai_embedding_batch, save_embedding_cache
from logic.gensim_w2v_vectorizer import GensimW2VVectorizer


def add_vectors_to_results(search_results, query, params: DotDict, descriptive_text_fields, map_data, timings):

    # using the code below leads to broken vectors for some reasons:
    # texts = [item.get("title", "") + " " + item.get("abstract", "") for item in results_part]
    # chunk_size = 30  # 30 -> 2.7GB GPU RAM (almost linear)
    # embeddings = np.zeros((0, 768))
    # for i in range(0, len(texts), chunk_size):
    #     embeddings = np.append(embeddings, get_embedding(texts[i:i+chunk_size]), axis=0)

    #texts = {item["DOI"]: item.get("title", "") + " " + item.get("abstract", "")[:2000] for item in results_part}
    #embeddings = get_openai_embedding_batch(texts)
    #save_embedding_cache()

    if params.vectorize.vectorizer in ["pubmedbert", "openai"]:
        query_embedding = get_embedding(query)
        absclust_schema_id = 1
        if params.search.search_strategy == "vector" or params.schema_id != absclust_schema_id:
            # the vectors are already in the search results
            return

        map_data["progress"]["total_steps"] = len(search_results)

        for i, item in enumerate(search_results):
            #item_embedding = embeddings[item["DOI"]]
            item_embedding = get_embedding(item.get("title", "") + " " + item.get("abstract", ""), item["DOI"]).tolist()
            item["pubmed_vector"] = item_embedding
            item["_score"] = np.dot(query_embedding, item_embedding)

            map_data["progress"]["current_step"] = i

        timings.log("adding vectors")

    elif params.vectorize.vectorizer == "gensim_w2v_tf_idf":
        map_data["progress"]["step_title"] = "Training model"
        corpus = [" ".join([item[field] for field in descriptive_text_fields]) for item in search_results]
        vectorizer = GensimW2VVectorizer()
        vectorizer.prepare(corpus)
        timings.log("training w2v model")
        query_embedding = vectorizer.get_embedding(query)

        map_data["progress"]["step_title"] = "Generating vectors"
        map_data["progress"]["total_steps"] = len(search_results)

        for i, item in enumerate(search_results):
            text = " ".join([item[field] for field in descriptive_text_fields])
            item_embedding = vectorizer.get_embedding(text).tolist()
            item["w2v_vector"] = item_embedding
            item["_score"] = np.dot(query_embedding, item_embedding)

            map_data["progress"]["current_step"] = i
        timings.log("generating embeddings")
    else:
        logging.error("vectorizer unknown: " + params.vectorize.vectorizer)

    save_embedding_cache()
