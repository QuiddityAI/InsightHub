from copy import deepcopy
import logging
import time
from functools import lru_cache
from threading import Thread
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug import serving

import numpy as np

# for tsne:
# from sklearn.manifold import TSNE
import umap

from sklearn.feature_extraction.text import TfidfVectorizer
import hdbscan

from utils.model_client import get_embedding, get_openai_embedding_batch, save_embedding_cache
from utils.absclust_database_client import get_absclust_search_results, save_search_cache
from utils.gensim_w2v_vectorizer import GensimW2VVectorizer
from utils.cluster_title import ClusterTitles
from utils.tokenizer import tokenize
from utils.postprocess_search_results import enrich_search_results
from utils.collect_timings import Timings


# --- Set up: ---

app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

# exclude polling endpoints from logs (see https://stackoverflow.com/a/57413338):
parent_log_request = serving.WSGIRequestHandler.log_request

def log_request(self, *args, **kwargs):
    if self.path == '/api/map/result':
        return

    parent_log_request(self, *args, **kwargs)

serving.WSGIRequestHandler.log_request = log_request


# --- Routes: ---

@app.route('/api/query', methods=['POST'])
def query():
    params_str = json.dumps(request.json, indent=2)
    print(params_str)
    return _query(params_str)


@lru_cache()
def _query(params_str):
    params = json.loads(params_str)
    query = params.get("query")
    if not query:
        return "query parameter is missing", 400

    timings = Timings()

    # TODO: currently only first page is returned
    search_results = get_search_results_for_list(query.split(" OR "), limit=params.get("result_list_items_per_page", 10))
    timings.log("database query")

    search_results = enrich_search_results(search_results, query)
    timings.log("enriching results")

    result = {
        "items": search_results,
        "timings": timings.get_timestamps(),
    }
    return jsonify(result)


def get_search_results_for_list(queries: list[str], limit: int):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += cluster_cache[cluster_uid][:10]
            continue

        results_part = get_absclust_search_results(query, limit)
        results += results_part

    save_search_cache()

    return results


@app.route('/api/map', methods=['POST'])
def get_or_create_map_task():
    params = request.json
    query = params.get("query")
    if not query:
        return "query parameter is missing", 400

    task_id = json.dumps(params)

    if task_id not in mapping_tasks:
        task_params[task_id] = params
        mapping_tasks[task_id] = {
            "finished": False,
            "result": None,
            "progress": {
                "embeddings_available": False,
                "total_steps": 1,
                "current_step": 0
            },
        }
        thread = Thread(target = generate_map, args = (task_id,))
        thread.start()

    return jsonify({"task_id": task_id})


def generate_map(task_id):
    params = task_params[task_id]
    query = params.get("query")

    timings = Timings()

    elements = get_search_results_for_map(query.split(" OR "), limit=params.get("max_items_used_for_mapping", 3000), task_id=task_id)
    timings.log("database query")
    add_vectors_to_results(elements, query, task_id)
    timings.log("adding vectors")

    vectors = [e["vector"] for e in elements]
    distances = [e["distance"] for e in elements]
    citations = [e.get("citedby", 0) for e in elements]
    features = np.asarray(vectors)  # shape result_count x 768
    timings.log("convert to numpy")

    def on_umap_progress(working_in_embedding_space, current_iteration, total_iterations, embeddings):
        mapping_tasks[task_id]["progress"] = {
            "embeddings_available": working_in_embedding_space,
            "total_steps": total_iterations,
            "current_step": current_iteration,
        }
        projections = embeddings

        if working_in_embedding_space and projections is not None:
            positionsX = projections[:, 0]
            positionsY = projections[:, 1]

            result = {
                "item_details": [],
                "per_point_data": {
                    "positions_x": positionsX.tolist(),
                    "positions_y": positionsY.tolist(),
                    "cluster_ids": [-1] * len(positionsX),
                    "distances": distances,
                    "citations": citations,
                },
                "cluster_data": [],
                "timings": [],
            }
            mapping_tasks[task_id]["result"] = result

    # Note: UMAP computes all distance pairs when less than 4096 points and uses approximation above
    # Progress might only be available below 4096

    umap_parameters = params.get("dim_reducer_parameters", {})
    umap_task = umap.UMAP(random_state=99, min_dist=umap_parameters.get("min_dist", 0.05), n_epochs=umap_parameters.get("n_epochs", 500))
    projections = umap_task.fit_transform(features, on_progress_callback=on_umap_progress)
    timings.log("UMAP fit transform")

    cluster_labels = cluster_results(projections)
    timings.log("clustering")
    cluster_data = get_cluster_titles(cluster_labels, projections, elements, timings)
    timings.log("cluster title")

    positionsX = projections[:, 0]
    positionsY = projections[:, 1]
    cluster_id_per_point = cluster_labels

    result = {
        "per_point_data": {
            "positions_x": positionsX.tolist(),
            "positions_y": positionsY.tolist(),
            "cluster_ids": cluster_id_per_point.tolist(),
            "distances": distances,
            "citations": citations,
        },
        "cluster_data": cluster_data,
        "timings": timings.get_timestamps(),
    }

    # FIXME: this also stores vectors a second time in the cache (33MB per request)
    map_details[task_id] = elements

    mapping_tasks[task_id]["result"] = result
    mapping_tasks[task_id]["finished"] = True


def get_search_results_for_map(queries: list[str], limit: int, task_id: str=None):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += cluster_cache[cluster_uid]
            continue

        results_part = get_absclust_search_results(query, limit)
        results += results_part

    save_search_cache()
    return results


def add_vectors_to_results(search_results, query, task_id):
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

    if task_params[task_id]["vectorizer"] in ["pubmedbert", "openai"]:
        if task_id:
            mapping_tasks[task_id]["progress"]["total_steps"] = len(search_results)

        for i, item in enumerate(search_results):
            #item_embedding = embeddings[item["DOI"]]
            item_embedding = get_embedding(item.get("title", "") + " " + item.get("abstract", ""), item["DOI"]).tolist()
            item["vector"] = item_embedding
            item["distance"] = np.dot(query_embedding, item_embedding)

            if task_id:
                mapping_tasks[task_id]["progress"]["current_step"] = i

    elif task_params[task_id]["vectorizer"] == "gensim_w2v_tf_idf":

        corpus = [item["abstract"] for item in search_results]
        vectorizer = GensimW2VVectorizer()
        vectorizer.prepare(corpus)
        query_embedding = vectorizer.get_embedding(query)

        if task_id:
            mapping_tasks[task_id]["progress"]["total_steps"] = len(search_results)

        for i, item in enumerate(search_results):
            item_embedding = vectorizer.get_embedding(item.get("abstract", "")).tolist()
            item["vector"] = item_embedding
            item["distance"] = np.dot(query_embedding, item_embedding)

            if task_id:
                mapping_tasks[task_id]["progress"]["current_step"] = i

    else:
        logging.error("vectorizer unknown: " + task_params[task_id]["vectorizer"])

    save_embedding_cache()


def cluster_results(projections):
    clusterer = hdbscan.HDBSCAN(min_cluster_size=max(3, len(projections) // 50), min_samples=5)
    clusterer.fit(projections)
    return clusterer.labels_

last_cluster_id = 0
cluster_cache = {}  # cluster_id -> search_results


def get_cluster_titles(cluster_labels, projections, results, timings):
    global last_cluster_id, cluster_cache
    num_clusters = max(cluster_labels) + 1
    if num_clusters <= 0:
        return []
    texts_per_cluster = [""] * num_clusters
    points_per_cluster_x = [[] for i in range(num_clusters)]
    points_per_cluster_y = [[] for i in range(num_clusters)]
    results_by_cluster = [[] for i in range(num_clusters)]

    for result_index, cluster_index in enumerate(cluster_labels):
        if cluster_index <= -1: continue
        text = results[result_index]["title"] + " " + results[result_index]["abstract"]
        texts_per_cluster[cluster_index] += text
        points_per_cluster_x[cluster_index].append(projections[result_index][0])
        points_per_cluster_y[cluster_index].append(projections[result_index][1])
        results_by_cluster[cluster_index].append(results[result_index])
    timings.log("getting abstracts from disk")

    # highlight TF-IDF words:
    # tf_idf_helper = ClusterTitles()
    # vectorizer = TfidfVectorizer(stop_words="english")
    vectorizer = TfidfVectorizer(analyzer=tokenize, max_df=0.7)
    # vectorizer = TfidfVectorizer(analyzer=tf_idf_helper.tokenize)
    tf_idf_matrix = vectorizer.fit_transform(texts_per_cluster)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    cluster_data = []

    for cluster_index in range(num_clusters):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[cluster_index].toarray()[0])
        most_important_words = words[sort_indexes_of_important_words[-3:]][::-1]
        cluster_center = (float(np.mean(points_per_cluster_x[cluster_index])), float(np.mean(points_per_cluster_y[cluster_index])))
        last_cluster_id += 1
        cluster_uid = str(last_cluster_id)
        cluster_cache[cluster_uid] = results_by_cluster[cluster_index]
        cluster_title = ", ".join(list(most_important_words)) + f" ({len(results_by_cluster[cluster_index])})"
        cluster_data.append({"uid": cluster_uid, "title": cluster_title, "center": cluster_center})
    timings.log("Tf-Idf")

    return cluster_data


task_params = {}
mapping_tasks = {}
map_details = {}


@app.route('/api/map/result', methods=['POST'])
def get_map_html_result():
    task_id = request.json.get("task_id")
    if task_id not in mapping_tasks:
        logging.warning("task_id not found")
        return "task_id not found", 404

    result = mapping_tasks[task_id]

    # if result["finished"]:
    #     del umap_tasks[task_id]

    # TODO: if the task is never retrieved, it gets never deleted
    # instead go through tasks every few minutes and delete old ones

    return result


@app.route('/api/map/details', methods=['POST'])
def get_map_details():
    task_id = request.json.get("task_id")
    if task_id not in map_details:
        logging.warning("task_id not found")
        return "task_id not found", 404

    # transferring all titles takes is up to 1 MByte, so we are doing it in a separate endpoint
    # for this, we are copying the results here:
    # remove abstracts from search results to reduce size of response:
    item_details = deepcopy(map_details[task_id])
    for item in item_details:
        if "abstract" in item:
            del item["abstract"]
            del item["vector"]
    result = item_details

    # if result["finished"]:
    #     del umap_tasks[task_id]

    # TODO: if the task is never retrieved, it gets never deleted
    # instead go through tasks every few minutes and delete old ones

    return result


@app.route('/api/document/details', methods=['POST'])
def get_document_details():
    # FIXME: the abstract should be retrived from the database and not the "map details" cache,
    # as the cache would be empty already
    task_id = request.json.get("task_id")
    index = request.json.get("index")
    if task_id not in map_details or len(map_details[task_id]) <= index:
        logging.warning("task_id not found or index out of range")
        return "task_id not found", 404

    return map_details[task_id][index]


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55123', debug=True)
