from copy import deepcopy
import logging
import time
import re
from functools import lru_cache
import uuid
from threading import Thread

from flask import Flask, request, jsonify
from flask_cors import CORS

from utils.cluster_title import ClusterTitles
app = Flask(__name__)
CORS(app) # This will enable CORS for all routes

import numpy as np
from tqdm import tqdm

# for tsne:
# from sklearn.manifold import TSNE
import umap
import plotly.express as px

from sklearn.feature_extraction.text import TfidfVectorizer
import hdbscan


from utils.model_client import get_embedding, get_openai_embedding_batch, save_embedding_cache
from utils.absclust_client import get_absclust_search_results, save_search_cache


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


words_ignored_for_highlighting = ("on", "in", "using", "with", "the", "a", "of")


def enrich_search_results(results, query):
    corpus = []

    for i, item in enumerate(results):
        title = item["title"]
        abstract = item["abstract"]
        corpus.append(title + " " + abstract)
        for word in query.split(" "):
            if word in words_ignored_for_highlighting:
                continue
            # TODO: this breaks when title contains words like "bold" or "font"
            replacement = '<span class="font-bold">\\1</span>'
            title = re.sub(f"\\b({re.escape(word)})\\b", replacement, title, flags=re.IGNORECASE)
            abstract = re.sub(f"\\b({re.escape(word)})\\b", replacement, abstract, flags=re.IGNORECASE)
        results[i]["title_enriched"] = title
        results[i]["abstract_enriched"] = abstract.replace("\n", "<br>")

    # highlight TF-IDF words:
    vectorizer = TfidfVectorizer(stop_words="english")
    tf_idf_matrix = vectorizer.fit_transform(corpus)  # not numpy but scipy sparse array
    words = vectorizer.get_feature_names_out()

    for i, item in enumerate(results):
        # converting scipy sparse array to numpy using toarray() and selecting the only row [0]
        sort_indexes_of_important_words = np.argsort(tf_idf_matrix[i].toarray()[0])
        most_important_words = words[sort_indexes_of_important_words[-5:]][::-1]
        results[i]["most_important_words"] = list(most_important_words)
    return results


@app.route('/api/query', methods=['POST'])
def query():
    return _query(request.json.get("query"))


@lru_cache()
def _query(query):
    if not query:
        return jsonify({})

    timings = []
    t1 = time.time()
    search_results = get_search_results_for_list(query.split(" OR "), limit=10)
    t2 = time.time()
    timings.append({"part": "vector DB hybrid query", "duration": t2 - t1})

    search_results = enrich_search_results(search_results, query)
    t3 = time.time()
    timings.append({"part": "enriching results", "duration": t3 - t2})

    result = {
        "items": search_results,
        "timings": timings,
    }
    return jsonify(result)


def get_search_results_for_map(queries: list[str], limit: int, task_id: str=None):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += cluster_cache[cluster_uid]
            continue

        results_part = get_absclust_search_results(query, limit)

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

        if task_id:
            umap_tasks[task_id]["progress"]["total_steps"] = len(results_part)

        for i, item in enumerate(results_part):
            #item_embedding = embeddings[item["DOI"]]
            item_embedding = get_embedding(item.get("title", "") + " " + item.get("abstract", ""), item["DOI"]).tolist()
            item["vector"] = item_embedding
            item["distance"] = np.dot(query_embedding, item_embedding)

            if task_id:
                umap_tasks[task_id]["progress"]["current_step"] = i

        results += results_part

    save_search_cache()
    save_embedding_cache()

    return results


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

    t1 = time.time()
    for result_index, cluster_index in enumerate(cluster_labels):
        if cluster_index <= -1: continue
        text = results[result_index]["title"] + " " + results[result_index]["abstract"]
        texts_per_cluster[cluster_index] += text
        points_per_cluster_x[cluster_index].append(projections[result_index][0])
        points_per_cluster_y[cluster_index].append(projections[result_index][1])
        results_by_cluster[cluster_index].append(results[result_index])
    t2 = time.time()
    timings.append({"part": "getting abstracts from disk", "duration": t2 - t1})

    # highlight TF-IDF words:
    tf_idf_helper = ClusterTitles()
    vectorizer = TfidfVectorizer(stop_words="english")
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
    t3 = time.time()
    timings.append({"part": "Tf-Idf", "duration": t3 - t2})

    return cluster_data


umap_tasks = {}


@app.route('/api/map', methods=['POST'])
def map_html():
    query = request.json.get("query")
    if not query:
        return jsonify({})

    task_id = query # str(uuid.uuid4())

    if task_id in umap_tasks:
        return jsonify({"task_id": task_id})

    umap_tasks[task_id] = {
        "finished": False,
        "result": None,
        "progress": {"embeddings_available": False, "total_steps": 1, "current_step": 0},
    }

    thread = Thread(target = _finish_map_html, args = (task_id, query))
    thread.start()

    return jsonify({"task_id": task_id})


@app.route('/api/map/result', methods=['POST'])
def get_map_html_result():
    task_id = request.json.get("task_id")
    if task_id not in umap_tasks:
        logging.warning("task_id not found")
        return "task_id not found", 404

    result = umap_tasks[task_id]

    # if result["finished"]:
    #     del umap_tasks[task_id]

    # TODO: if the task is never retrieved, it gets never deleted
    # instead go through tasks every few minutes and delete old ones

    return result


def _finish_map_html(task_id, query):
    timings = []
    t1 = time.time()
    elements = get_search_results_for_map(query.split(" OR "), limit=3000, task_id=task_id)
    t2 = time.time()
    timings.append({"part": "vector DB pure vector query, limit 600", "duration": t2 - t1})

    vectors = [e["vector"] for e in elements]
    distances = [e["distance"] for e in elements]
    citations = [e.get("citedby", 0) for e in elements]

    features = np.asarray(vectors)  # shape 600x768
    t4 = time.time()
    timings.append({"part": "convert to numpy", "duration": t4 - t2})

    # tsne = TSNE(n_components=2, random_state=0)  # instant
    # projections = tsne.fit_transform(features)

    def on_progress(working_in_embedding_space, current_iteration, total_iterations, embeddings):
        umap_tasks[task_id]["progress"] = {
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
            umap_tasks[task_id]["result"] = result

    # Note: UMAP computes all distance pairs when less than 4096 points and uses approximation above
    # Progress might only be available below 4096

    projections = umap.UMAP(random_state=99, min_dist=0.05, n_epochs=500).fit_transform(features, on_progress_callback=on_progress)

    # callback for intermediate results can be added here: https://github.com/lmcinnes/umap/blob/master/umap/layouts.py#L417
    t6 = time.time()
    timings.append({"part": "UMAP fit transform", "duration": t6 - t4})
    cluster_labels = cluster_results(projections)
    cluster_data = get_cluster_titles(cluster_labels, projections, elements, timings)
    t7 = time.time()

    positionsX = projections[:, 0]
    positionsY = projections[:, 1]
    cluster_id_per_point = cluster_labels

    # remove abstracts from search results to reduce size of response:

    item_details = deepcopy(elements)

    for item in item_details:
        if "abstract" in item:
            del item["abstract"]

    result = {
        "item_details": item_details,
        "per_point_data": {
            "positions_x": positionsX.tolist(),
            "positions_y": positionsY.tolist(),
            "cluster_ids": cluster_id_per_point.tolist(),
            "distances": distances,
            "citations": citations,
        },
        "cluster_data": cluster_data,
        "timings": timings,
    }

    umap_tasks[task_id]["result"] = result
    umap_tasks[task_id]["finished"] = True


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='55123', debug=True)
