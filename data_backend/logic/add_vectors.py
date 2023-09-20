import logging
import os
import pickle

import numpy as np

from utils.dotdict import DotDict

from logic.model_client import get_embedding, save_embedding_cache
from logic.gensim_w2v_vectorizer import GensimW2VVectorizer


def add_w2v_vectors(search_results, query, params: DotDict, descriptive_text_fields, map_data, vectorize_stage_params_hash, timings):
    # last_w2v_embeddings_file_path might be used if search and vectorize settings are the same
    # or when narrowing down on subcluster of bigger map
    last_w2v_embeddings_file_path = map_data['results']['w2v_embeddings_file_path']
    if last_w2v_embeddings_file_path and os.path.exists(last_w2v_embeddings_file_path):
        with open(last_w2v_embeddings_file_path, "rb") as f:
            embeddings = pickle.load(f)
        try:
            query_embedding = embeddings["query"]
            for item in search_results:
                item_embedding = embeddings[item["_id"]]
                item["w2v_vector"] = item_embedding
                item["_score"] = np.dot(query_embedding, item_embedding)
        except KeyError as e:
            logging.warning("Existing w2v embedding file is missing an item:")
            logging.warning(e)
            # falling through to training model again from scratch
            pass
        else:
            timings.log("reusing existing w2v embeddings")
            return

    map_data["progress"]["step_title"] = "Training model"
    corpus = [" ".join([item.get(field, "") for field in descriptive_text_fields]) for item in search_results]
    vectorizer = GensimW2VVectorizer()
    vectorizer.prepare(corpus)
    timings.log("training w2v model")

    map_data["progress"]["step_title"] = "Generating vectors"
    map_data["progress"]["total_steps"] = len(search_results)
    map_data["progress"]["current_step"] = 0

    embeddings = {}
    query_embedding = vectorizer.get_embedding(query)
    embeddings["query"] = query_embedding
    for i, item in enumerate(search_results):
        text = " ".join([item.get(field, "") for field in descriptive_text_fields])
        item_embedding = vectorizer.get_embedding(text).tolist()
        item["w2v_vector"] = item_embedding
        item["_score"] = np.dot(query_embedding, item_embedding)
        embeddings[item["_id"]] = item_embedding

        map_data["progress"]["current_step"] = i

    w2v_embeddings_file_path = f"map_data/w2v_embeddings_{vectorize_stage_params_hash}.pkl"
    with open(w2v_embeddings_file_path, "wb") as f:
        pickle.dump(embeddings, f)
    map_data['results']['w2v_embeddings_file_path'] = w2v_embeddings_file_path

    timings.log("generating w2v embeddings")


def add_vectors_to_results_from_external_db(search_results, query, params: DotDict, descriptive_text_fields, map_data, schema, timings):

    # using the code below leads to broken vectors for some reasons:
    # texts = [item.get("title", "") + " " + item.get("abstract", "") for item in results_part]
    # chunk_size = 30  # 30 -> 2.7GB GPU RAM (almost linear)
    # embeddings = np.zeros((0, 768))
    # for i in range(0, len(texts), chunk_size):
    #     embeddings = np.append(embeddings, get_embedding(texts[i:i+chunk_size]), axis=0)

    #texts = {item["DOI"]: item.get("title", "") + " " + item.get("abstract", "")[:2000] for item in results_part}
    #embeddings = get_openai_embedding_batch(texts)
    #save_embedding_cache()

    absclust_schema_id = 1
    if params.vectorize.vectorizer not in ["pubmedbert"] or params.schema_id != absclust_schema_id:
        return

    if query:
        query_embedding = get_embedding(query)

    map_data["progress"]["step_title"] = "Generating vectors"
    map_data["progress"]["total_steps"] = len(search_results)
    map_data["progress"]["current_step"] = 0

    for i, item in enumerate(search_results):
        item_embedding = get_embedding(" ".join([item[field] for field in descriptive_text_fields]), item[schema.primary_key]).tolist()
        item["pubmed_vector"] = item_embedding
        if query:
            item["_score"] = np.dot(query_embedding, item_embedding)

        map_data["progress"]["current_step"] = i

    timings.log("adding vectors")

    save_embedding_cache()
