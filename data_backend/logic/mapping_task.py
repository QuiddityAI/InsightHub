from copy import deepcopy
from hashlib import md5
import logging
from threading import Thread
import json
from uuid import UUID
import os
from functools import lru_cache
import time

import numpy as np
from PIL import Image

# import umap  # imported lazily when used

from utils.collect_timings import Timings
from utils.helpers import normalize_array, polar_to_cartesian
from utils.dotdict import DotDict

from database_client.absclust_database_client import get_absclust_search_results, save_search_cache, get_absclust_item_by_id
from database_client.django_client import get_object_schema, get_stored_map_data
from database_client.vector_search_engine_client import VectorSearchEngineClient
from database_client.object_storage_client import ObjectStorageEngineClient

from logic.generator_functions import get_generator_function
from logic.add_vectors import add_vectors_to_results
from logic.clusters_and_titles import clusterize_results, get_cluster_titles


ABSCLUST_SCHEMA_ID = 1


# global temp storage:
local_maps = {}

# old global vars:
task_params = {}
mapping_tasks = {}
map_details = {}
cluster_cache = {}  # cluster_id -> search_results


def get_or_create_map(params):
    map_id = md5(json.dumps(params).encode()).hexdigest()

    if map_id not in local_maps:
        map_data = get_stored_map_data(map_id)
        if map_data:
            local_maps[map_id] = map_data
        else:
            map_data = {
                "last_accessed": time.time(),
                "finished": False,
                "is_stored": False,
                "parameters": params,
                "last_parameters": {
                        # schema_id, user_id
                        # search settings
                        # vectorize settings
                        # projection settings
                        # render settings
                    },
                "progress": {
                    "total_steps": 1,
                    "current_step": 0,
                    "step_title": "Preparation",
                    "projections_available": False,
                },
                "map_rendering": None,
                "results": {
                    "per_point_data": {
                        "item_ids": [],
                        "scores": [],
                        "hover_label_data": [],
                        "positions_x": [],
                        "positions_y": [],
                        "cluster_ids": [],
                        "point_sizes": [],

                        "point_colors": [],
                        "point_roughness": [],
                        "point_shape": [],
                    },
                    "clusters": {
                        # x: { id: x, title: foo, centerX, centerY }, for each cluster
                    },
                    "texture_atlas_path": None,
                    "w2v_embeddings_file_path": None,
                },
            }
            local_maps[map_id] = map_data
            thread = Thread(target = generate_map, args = (map_id,))
            thread.start()

    return map_id


def generate_map(map_id):
    timings = Timings()

    map_data = local_maps[map_id]
    params = DotDict(map_data["parameters"])

    query = params.search_settings.query
    limit = params.vectorize_settings.max_items_used_for_mapping
    schema_id = params.schema_id
    search_vector_field = params.search_settings.search_vector_field
    map_vector_field = params.vectorize_settings.map_vector_field
    if not all([query, limit, schema_id, search_vector_field, map_vector_field]):
        map_data['progress']['step_title'] = "a parameter is missing"
        raise ValueError("a parameter is missing")
    schema = get_object_schema(schema_id)
    map_data["hover_label_rendering"] = schema.hover_label_rendering

    additional_fields = set(schema.hover_label_rendering.required_fields or [])
    if schema.thumbnail_image:
        additional_fields.add(schema.thumbnail_image)
    additional_fields = additional_fields.union(schema.descriptive_text_fields)
    additional_fields = list(additional_fields)
    timings.log("preparation")

    map_data['progress']['step_title'] = "Getting search results"
    search_results = get_search_results_for_map(schema, search_vector_field, map_vector_field, query.split(" OR "), additional_fields, limit)
    timings.log("database query")

    map_data["results"]["per_point_data"]["item_ids"] = [item["_id"] for item in search_results]

    # eventually, the vectors should come directly from the database
    # but for the AbsClust database, the vectors need to be added on-demand:
    if schema.id == ABSCLUST_SCHEMA_ID:
        map_data['progress']['step_title'] = "Generating vectors"
        add_vectors_to_results(search_results, query, params, schema.descriptive_text_fields, map_data, timings)

    vectors = np.asarray([e[map_vector_field] for e in search_results])  # shape result_count x 768
    scores = [e["score"] for e in search_results]
    map_data["results"]["per_point_data"]["scores"] = scores
    point_sizes = [e.get(params.render_settings.point_size_field) for e in search_results] if params.render_settings.point_size_field else [1] * len(search_results)
    map_data["results"]["per_point_data"]["point_sizes"] = point_sizes
    map_data["results"]["per_point_data"]["cluster_ids"] = [-1] * len(scores),
    timings.log("convert to numpy")

    umap_parameters = params.get("projection_settings", {})

    def on_umap_progress(working_in_embedding_space, current_iteration, total_iterations, projections):
        map_data["progress"] = {
            "total_steps": total_iterations,
            "current_step": current_iteration,
            "step_title": "UMAP 2/2: finetuning" if working_in_embedding_space else "UMAP 1/2: pair-wise distances",
            "embeddings_available": working_in_embedding_space,
        }

        if working_in_embedding_space and projections is not None:
            if umap_parameters.get("shape") == "1d_plus_distance_polar":
                projections = np.column_stack(polar_to_cartesian(1 - normalize_array(scores), normalize_array(projections[:, 0]) * np.pi * 2))

            map_data["results"]["per_point_data"]["positions_x"] = projections[:, 0].tolist()
            map_data["results"]["per_point_data"]["positions_y"] = projections[:, 1].tolist()

    # Note: UMAP computes all distance pairs when less than 4096 points and uses approximation above
    # Progress might only be available below 4096

    map_data['progress']['step_title'] = "UMAP Preparation"
    target_dimensions = 1 if umap_parameters.get("shape") == "1d_plus_distance_polar" else 2
    import umap
    umap_task = umap.UMAP(n_components=target_dimensions, random_state=99, min_dist=umap_parameters.get("min_dist", 0.05), n_epochs=umap_parameters.get("n_epochs", 500))
    projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)
    timings.log("UMAP fit transform")

    map_data['progress']['step_title'] = "Clusterize results"
    cluster_id_per_point = clusterize_results(projections)
    timings.log("clustering")

    if umap_parameters.get("shape") == "1d_plus_distance_polar":
        projections = np.column_stack(polar_to_cartesian(1 - normalize_array(scores), normalize_array(projections[:, 0]) * np.pi * 2))

    map_data["results"]["per_point_data"]["positions_x"] = projections[:, 0].tolist()
    map_data["results"]["per_point_data"]["positions_y"] = projections[:, 1].tolist()
    map_data["results"]["per_point_data"]["cluster_ids"] = cluster_id_per_point.tolist()

    hover_label_data_total = []
    for item in search_results:
        hover_label_data = {}
        hover_label_data['_id'] = item['_id']
        for field in schema.hover_label_rendering.required_fields:
            hover_label_data[field] = item.get(field, None)
        hover_label_data_total.append(hover_label_data)

    map_data["results"]["per_point_data"]["hover_label_data"] = hover_label_data_total

    map_data['progress']['step_title'] = "Find cluster titles"
    cluster_data = get_cluster_titles(cluster_id_per_point, projections, search_results, schema.descriptive_text_fields, timings, cluster_cache)
    timings.log("cluster title")

    map_data["results"]["clusters"] = cluster_data

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
        atlas_filename = f"map_data/atlas_{query}.png"
        atlas.save(atlas_filename)
        map_data["results"]["texture_atlas_path"] = atlas_filename

    timings.log("generating texture atlas")

    map_data["results"]["timings"] = timings.get_timestamps()
    map_data["finished"] = True


def get_search_results_for_map(schema: DotDict, search_vector_field: str, map_vector_field: str, queries: list[str], additional_fields: list[str], limit: int):
    results = []

    for query in queries:
        if query.startswith("cluster_id: "):
            cluster_uid = query.split("cluster_id: ")[1].split(" (")[0]
            results += deepcopy(cluster_cache[cluster_uid])
            continue

        if schema.id == ABSCLUST_SCHEMA_ID:
            results += get_absclust_search_results(query, additional_fields, limit)
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


def get_map_results(map_id) -> dict | None:
    if map_id not in local_maps:
        map_data = get_stored_map_data(map_id)
        if map_data:
            local_maps[map_id] = map_data
        else:
            logging.warning("map_id not found")
            return None

    result = local_maps[map_id]
    result["last_accessed"] = time.time()
    # TODO: go through local_maps every hour and delete that ones that weren't been accessed in the last hour

    return result


def get_document_details(task_id, index):
    # FIXME: the abstract should be retrived from the database and not the "map details" cache,
    # as the cache would be empty already
    if task_id not in map_details or len(map_details[task_id]) <= index:
        logging.warning("task_id not found or index out of range")
        return None

    return map_details[task_id][index]


@lru_cache
def get_document_details_by_id(schema_id: int, item_id: str, fields: tuple[str]):
    if schema_id == ABSCLUST_SCHEMA_ID:
        return get_absclust_item_by_id(item_id)

    object_storage_client = ObjectStorageEngineClient.get_instance()
    items = object_storage_client.get_items_by_ids(schema_id, [UUID(item_id)], fields=fields)
    if not items:
        return None

    return items[0]
