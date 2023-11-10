import logging
import math
import os
import pickle
import time

import numpy as np

from utils.dotdict import DotDict
from utils.field_types import FieldType
from utils.helpers import join_text_source_fields

from logic.model_client import save_embedding_cache, embedding_cache
from logic.gensim_w2v_vectorizer import GensimW2VVectorizer
from logic.generate_missing_values import generate_missing_values_for_given_elements
from logic.extract_pipeline import get_pipeline_steps
from logic.generator_functions import get_generator_function_from_field
from logic.search_common import get_required_fields


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
    corpus = [join_text_source_fields(item, descriptive_text_fields) for item in search_results]
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
        text = join_text_source_fields(item, descriptive_text_fields)
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


def add_missing_map_vectors(search_results, query, params: DotDict, map_data, dataset, timings):
    map_data["progress"]["step_title"] = "Generating vectors"
    map_data["progress"]["total_steps"] = len(search_results)
    map_data["progress"]["current_step"] = 0

    map_vector_field = dataset.object_fields[params.vectorize.map_vector_field]
    t1 = time.time()

    # try to get embeddings from cache:
    for item in search_results:
        if item.get(map_vector_field.identifier) is not None:
            continue
        cache_key = str(dataset.id) + item['_id'] + map_vector_field.identifier
        cached_embedding = embedding_cache.get(cache_key, None)
        if cached_embedding is not None:
            item[map_vector_field.identifier] = cached_embedding

    if not all([item.get(map_vector_field.identifier) is not None for item in search_results]):
        # if some or all vectors are still missing, generate them:
        batch_size = 128
        pipeline_steps, required_fields, _ = get_pipeline_steps(dataset, only_fields=[map_vector_field.identifier])
        available_fields = get_required_fields(dataset, params.vectorize_settings, "map")
        missing_fields = required_fields - set(available_fields)
        if missing_fields:
            logging.warning(f"Some fields are missing in the search result data to generate missing vectors: {missing_fields}")
        for batch_number in range(math.ceil(len(search_results) / batch_size)):
            elements = search_results[batch_number*batch_size : (batch_number+1) * batch_size]
            changed_fields = generate_missing_values_for_given_elements(pipeline_steps, elements)
            for i, item in enumerate(elements):
                if map_vector_field.identifier in changed_fields[i]:
                    cache_key = str(dataset.id) + item['_id'] + map_vector_field.identifier
                    embedding_cache[cache_key] = item[map_vector_field.identifier]
            map_data["progress"]["current_step"] = batch_number * batch_size
        save_embedding_cache()

    duration_per_item = (time.time() - t1) / len(search_results)
    timings.log(f"adding missing vectors ({duration_per_item * 1000:.1f} ms per item)")

    # check if scores need to be re-calculated:
    scores = [item.get('_score') for item in search_results]
    if query and map_vector_field.generator and map_vector_field.generator.input_type == FieldType.TEXT \
        and (not all([score is not None for score in scores]) \
            or np.min(scores) == np.max(scores)):
        map_data["progress"]["step_title"] = "Generating scores"
        map_data["progress"]["total_steps"] = len(search_results)
        map_data["progress"]["current_step"] = 0

        generator_function = get_generator_function_from_field(map_vector_field)
        query_embedding = generator_function([[query]])[0]

        for i, item in enumerate(search_results):
            item_embedding = item[map_vector_field.identifier]
            item["_score"] = np.dot(query_embedding, item_embedding)

            map_data["progress"]["current_step"] = i
        timings.log("adding scores")
