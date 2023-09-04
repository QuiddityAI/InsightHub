from copy import deepcopy
import logging
from threading import Thread
import json
from uuid import UUID
import os

import numpy as np
from PIL import Image

# import umap  # imported lazily when used

from utils.collect_timings import Timings
from utils.helpers import normalize_array, polar_to_cartesian
from utils.dotdict import DotDict

from database_client.absclust_database_client import get_absclust_search_results, save_search_cache
from database_client import weaviate_database_client
from database_client.django_client import get_object_schema
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.object_storage_client import ObjectStorageEngineClient

from logic.generator_functions import get_generator_function
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
                "current_step": 0,
                "step_title": "Preparation",
            },
        }
        thread = Thread(target = generate_map, args = (task_id,))
        thread.start()

    return task_id


def generate_map(task_id):
    timings = Timings()

    params = task_params[task_id]
    query = params.get("query")
    limit = params.get("max_items_used_for_mapping")
    schema_id = params.get("schema_id")
    search_vector_field = params.get("search_vector_field")
    map_vector_field = params.get("map_vector_field")
    if not all([query, limit, schema_id, search_vector_field, map_vector_field]):
        mapping_tasks[task_id]['progress']['step_title'] = "a parameter is missing"
        raise ValueError("a parameter is missing")

    schema = get_object_schema(schema_id)
    map_rendering = DotDict(json.loads(schema.map_rendering))
    additional_fields = map_rendering.required_fields or []
    if schema.thumbnail_image:
        additional_fields.append(schema.thumbnail_image)
    timings.log("preparation")

    mapping_tasks[task_id]['progress']['step_title'] = "Getting search results"
    search_results = get_search_results_for_map(schema, search_vector_field, map_vector_field, query.split(" OR "), additional_fields, limit)
    timings.log("database query")

    # eventually, the vectors should come directly from the database
    # but for the AbsClust database, the vectors need to be added on-demand:
    absclust_schema_id = 1
    if schema.id == absclust_schema_id:
        mapping_tasks[task_id]['progress']['step_title'] = "Generating vectors"
        add_vectors_to_results(search_results, query, task_params[task_id], mapping_tasks[task_id], timings)

    vectors = np.asarray([e[map_vector_field] for e in search_results])  # shape result_count x 768
    distances = [e["score"] for e in search_results]
    point_sizes = [e.get(map_rendering.point_size_field) for e in search_results] if map_rendering.point_size_field else [1] * len(search_results)
    timings.log("convert to numpy")

    umap_parameters = params.get("dim_reducer_parameters", {})

    def on_umap_progress(working_in_embedding_space, current_iteration, total_iterations, projections):
        mapping_tasks[task_id]["progress"] = {
            "embeddings_available": working_in_embedding_space,
            "total_steps": total_iterations,
            "current_step": current_iteration,
            "step_title": "UMAP 2/2: finetuning" if working_in_embedding_space else "UMAP 1/2: pair-wise distances",
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
                    "point_sizes": point_sizes,
                },
                "cluster_data": [],
                "rendering": map_rendering,
                "timings": [],
            }
            mapping_tasks[task_id]["result"] = result

    # Note: UMAP computes all distance pairs when less than 4096 points and uses approximation above
    # Progress might only be available below 4096

    mapping_tasks[task_id]['progress']['step_title'] = "UMAP Preparation"
    target_dimensions = 1 if umap_parameters.get("shape") == "1d_plus_distance_polar" else 2
    import umap
    umap_task = umap.UMAP(n_components=target_dimensions, random_state=99, min_dist=umap_parameters.get("min_dist", 0.05), n_epochs=umap_parameters.get("n_epochs", 500))
    """projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)
  File "/home/tim/.local/share/virtualenvs/visual-data-map-Xo4c37dQ/lib/python3.10/site-packages/umap/u
map_.py", line 2794, in fit_transform
    self.fit(X, y, on_progress_callback=on_progress_callback)
  File "/home/tim/.local/share/virtualenvs/visual-data-map-Xo4c37dQ/lib/python3.10/site-packages/umap/u
map_.py", line 2704, in fit
    self.embedding_, aux_data = self._fit_embed_data(
  File "/home/tim/.local/share/virtualenvs/visual-data-map-Xo4c37dQ/lib/python3.10/site-packages/umap/u
map_.py", line 2738, in _fit_embed_data
    return simplicial_set_embedding(
  File "/home/tim/.local/share/virtualenvs/visual-data-map-Xo4c37dQ/lib/python3.10/site-packages/umap/u
map_.py", line 1076, in simplicial_set_embedding
    graph.data[graph.data < (graph.data.max() / float(n_epochs))] = 0.0
  File "/home/tim/.local/share/virtualenvs/visual-data-map-Xo4c37dQ/lib/python3.10/site-packages/numpy/
core/_methods.py", line 41, in _amax
    return umr_maximum(a, axis, None, out, keepdims, initial, where)
ValueError: zero-size array to reduction operation maximum which has no identity"""
    projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)
    timings.log("UMAP fit transform")

    mapping_tasks[task_id]['progress']['step_title'] = "Clusterize results"
    cluster_id_per_point = clusterize_results(projections)
    timings.log("clustering")

    if umap_parameters.get("shape") == "1d_plus_distance_polar":
        projections = np.column_stack(polar_to_cartesian(1 - normalize_array(distances), normalize_array(projections[:, 0]) * np.pi * 2))

    mapping_tasks[task_id]['progress']['step_title'] = "Find cluster titles"
    cluster_data = []  # get_cluster_titles(cluster_id_per_point, projections, search_results, timings, cluster_cache)
    timings.log("cluster title")

    result = {
        "per_point_data": {
            "positions_x": projections[:, 0].tolist(),
            "positions_y": projections[:, 1].tolist(),
            "cluster_ids": cluster_id_per_point.tolist(),
            "distances": distances,
            "point_sizes": point_sizes,
        },
        "cluster_data": cluster_data,
        "rendering": map_rendering,
        "timings": timings.get_timestamps(),
    }
    mapping_tasks[task_id]["result"] = result

    # don't store vectors again: (up to 33MB for 1.6k items)
    for item in search_results:
        if map_vector_field in item:
            del item[map_vector_field]

    map_details[task_id] = search_results
    timings.log("store result")

    # texture atlas:
    thumbnail_field = schema.thumbnail_image
    if thumbnail_field:
        atlas = Image.new("RGBA", (2048, 2048))
        for i, item in enumerate(search_results):
            if item[thumbnail_field] and os.path.exists(item[thumbnail_field]):
                image = Image.open(item[thumbnail_field])
                image.thumbnail((32, 32))
                image = image.resize((32, 32))
                imagesPerLine = (2048/32)
                posRow: int = int(i / imagesPerLine)
                posCol: int = int(i % imagesPerLine)
                atlas.paste(image, (posCol * 32, posRow * 32))
                image.close()
            else:
                logging.warning(f"Image file doesn't exist: {item[thumbnail_field]}")
                # FIXME: needs to be a different image each time
                # textures.append(['thumbnail_placeholder.png', 32, 32])
        atlas_filename = f"atlas_{query}.png"
        atlas.save(atlas_filename)
        mapping_tasks[task_id]["result"]["texture_atlas_path"] = atlas_filename

    timings.log("generating texture atlas")

    mapping_tasks[task_id]["finished"] = True


def get_search_results_for_map(schema: DotDict, search_vector_field: str, map_vector_field: str, queries: list[str], additional_fields: list[str], limit: int):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += deepcopy(cluster_cache[cluster_uid])
            continue

        absclust_schema_id = 1
        if schema.id == absclust_schema_id:
            results += get_absclust_search_results(query, limit)
            continue

        generator = schema.object_fields[search_vector_field].generator
        generator_function = get_generator_function(generator.identifier, schema.object_fields[search_vector_field].generator_parameters)
        query_vector = generator_function([query])[0]

        vector_db_client = VectorSearchEngineClient.get_instance()
        criteria = {}  # TODO: add criteria
        return_vectors = search_vector_field == map_vector_field
        vector_search_result = vector_db_client.get_items_near_vector(schema.id, search_vector_field, query_vector, criteria, return_vectors=return_vectors, limit=limit)
        ids = [UUID(item.id) for item in vector_search_result]

        object_storage_client = ObjectStorageEngineClient.get_instance()
        if search_vector_field != map_vector_field:
            additional_fields.append(map_vector_field)
        object_storage_result = object_storage_client.get_items_by_ids(schema.id, ids, fields=additional_fields)

        for result_item, vector_search_result in zip(object_storage_result, vector_search_result):
            result_item['score'] = vector_search_result.score
            if search_vector_field == map_vector_field:
                result_item[map_vector_field] = vector_search_result.vector[search_vector_field]

        results += object_storage_result

    save_search_cache()
    return results


# TODO: this method shouldn't be here (but currently it has for the cluster_cache)
def get_search_results_for_list(schema: DotDict, vector_field: str, queries: list[str], additional_fields: list[str], limit: int, page: int):
    results = []

    for query in queries:
        # TODO: re-implement with map model as store for clusters
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += cluster_cache[cluster_uid][:10]
            continue

        absclust_schema_id = 1
        if schema.id == absclust_schema_id:
            results += get_absclust_search_results(query, limit)
            continue

        generator = schema.object_fields[vector_field].generator
        generator_function = get_generator_function(generator.identifier, schema.object_fields[vector_field].generator_parameters)
        query_vector = generator_function([query])[0]

        vector_db_client = VectorSearchEngineClient.get_instance()
        criteria = {}  # TODO: add criteria
        vector_search_result = vector_db_client.get_items_near_vector(schema.id, vector_field, query_vector, criteria, return_vectors=False, limit=limit)
        ids = [UUID(item.id) for item in vector_search_result]

        object_storage_client = ObjectStorageEngineClient.get_instance()
        object_storage_result = object_storage_client.get_items_by_ids(schema.id, ids, fields=additional_fields)
        results += object_storage_result

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
