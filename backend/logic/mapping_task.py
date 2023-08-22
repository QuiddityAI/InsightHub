from copy import deepcopy
import logging
from threading import Thread
import json

import numpy as np

# for tsne:
# from sklearn.manifold import TSNE
import umap

from utils.collect_timings import Timings
from utils.helpers import normalize_array, polar_to_cartesian

from database_client.absclust_database_client import get_absclust_search_results, save_search_cache
from database_client import weaviate_database_client

from logic.add_vectors import add_vectors_to_results
from logic.clusters_and_titles import clusterize_results, get_cluster_titles
from logic.model_client import get_embedding


# global caches:
task_params = {}
mapping_tasks = {}
map_details = {}
cluster_cache = {}  # cluster_id -> search_results


def get_or_create_mapping_task(params):
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

    return task_id


def generate_map(task_id):
    params = task_params[task_id]
    query = params.get("query")

    timings = Timings()

    search_results = get_search_results_for_map(query.split(" OR "), limit=params.get("max_items_used_for_mapping", 3000), params=params, task_id=task_id)
    timings.log("database query")

    # eventually, the vectors should come directly from the database
    # but for the AbsClust database, the vectors need to be added on-demand:
    add_vectors_to_results(search_results, query, task_params[task_id], mapping_tasks[task_id])
    timings.log("adding vectors")

    vectors = np.asarray([e["vector"] for e in search_results])  # shape result_count x 768
    distances = [e["distance"] for e in search_results]
    citations = [e.get("citedby", 0) for e in search_results]
    timings.log("convert to numpy")

    umap_parameters = params.get("dim_reducer_parameters", {})

    def on_umap_progress(working_in_embedding_space, current_iteration, total_iterations, projections):
        mapping_tasks[task_id]["progress"] = {
            "embeddings_available": working_in_embedding_space,
            "total_steps": total_iterations,
            "current_step": current_iteration,
        }

        if working_in_embedding_space and projections is not None:
            if umap_parameters.get("shape") == "1d_plus_distance_polar":
                projections = np.column_stack(polar_to_cartesian(1 - normalize_array(distances), normalize_array(projections[:, 0]) * np.pi * 2))

            result = {
                "per_point_data": {
                    "positions_x": projections[:, 0].tolist(),
                    "positions_y": projections[:, 1].tolist(),
                    "cluster_ids": [-1] * len(distances),
                    "distances": distances,
                    "citations": citations,
                },
                "cluster_data": [],
                "timings": [],
            }
            mapping_tasks[task_id]["result"] = result

    # Note: UMAP computes all distance pairs when less than 4096 points and uses approximation above
    # Progress might only be available below 4096

    target_dimensions = 1 if umap_parameters.get("shape") == "1d_plus_distance_polar" else 2
    umap_task = umap.UMAP(n_components=target_dimensions, random_state=99, min_dist=umap_parameters.get("min_dist", 0.05), n_epochs=umap_parameters.get("n_epochs", 500))
    projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)
    timings.log("UMAP fit transform")

    cluster_id_per_point = clusterize_results(projections)
    timings.log("clustering")

    if umap_parameters.get("shape") == "1d_plus_distance_polar":
        projections = np.column_stack(polar_to_cartesian(1 - normalize_array(distances), normalize_array(projections[:, 0]) * np.pi * 2))

    cluster_data = get_cluster_titles(cluster_id_per_point, projections, search_results, timings, cluster_cache)
    timings.log("cluster title")

    result = {
        "per_point_data": {
            "positions_x": projections[:, 0].tolist(),
            "positions_y": projections[:, 1].tolist(),
            "cluster_ids": cluster_id_per_point.tolist(),
            "distances": distances,
            "citations": citations,
        },
        "cluster_data": cluster_data,
        "timings": timings.get_timestamps(),
    }

    # don't store vectors again: (up to 33MB for 1.6k items)
    for item in search_results:
        if "vector" in item:
            del item["vector"]

    map_details[task_id] = search_results

    mapping_tasks[task_id]["result"] = result
    mapping_tasks[task_id]["finished"] = True


def get_search_results_for_map(queries: list[str], limit: int, params:dict, task_id: str=None):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += deepcopy(cluster_cache[cluster_uid])
            continue

        if params["selected_database"] == "absclust":
            results_part = get_absclust_search_results(query, limit)
        elif params["selected_database"] == "pubmed":
            vector = get_embedding(query)
            results_part = weaviate_database_client.get_results_for_map(query, vector, limit)
        results += results_part

    save_search_cache()
    return results


# TODO: this method shouldn't be here (but currently it has for the cluster_cache)
def get_search_results_for_list(queries: list[str], limit: int, params: dict):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += cluster_cache[cluster_uid][:10]
            continue

        if params["selected_database"] == "absclust":
            results_part = get_absclust_search_results(query, limit)
        elif params["selected_database"] == "pubmed":
            vector = get_embedding(query)
            results_part = weaviate_database_client.get_results_for_list(query, vector, limit)
        results += results_part

    save_search_cache()

    return results


def get_mapping_task_results(task_id):
    if task_id not in mapping_tasks:
        logging.warning("task_id not found")
        return None

    result = mapping_tasks[task_id]

    # if result["finished"]:
    #     del umap_tasks[task_id]

    # TODO: if the task is never retrieved, it gets never deleted
    # instead go through tasks every few minutes and delete old ones

    return result


def get_map_details(task_id):
    if task_id not in map_details:
        logging.warning("task_id not found")
        return None

    # transferring all titles takes is up to 1 MByte, so we are doing it in a separate endpoint
    # for this, we are copying the results here:
    # remove abstracts from search results to reduce size of response:
    item_details = deepcopy(map_details[task_id])
    for item in item_details:
        if "abstract" in item:
            del item["abstract"]
    result = item_details

    # if result["finished"]:
    #     del umap_tasks[task_id]

    # TODO: if the task is never retrieved, it gets never deleted
    # instead go through tasks every few minutes and delete old ones

    return result


def get_document_details(task_id, index):
    # FIXME: the abstract should be retrived from the database and not the "map details" cache,
    # as the cache would be empty already
    if task_id not in map_details or len(map_details[task_id]) <= index:
        logging.warning("task_id not found or index out of range")
        return None

    return map_details[task_id][index]
