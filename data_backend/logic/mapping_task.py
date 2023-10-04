from copy import deepcopy
import logging
from threading import Thread
import json
import os
import time

import numpy as np
from PIL import Image

# import umap  # imported lazily when used

from utils.collect_timings import Timings
from utils.helpers import normalize_array, polar_to_cartesian
from utils.dotdict import DotDict

from database_client.django_client import get_object_schema, get_stored_map_data

from logic.add_vectors import add_missing_map_vectors, add_w2v_vectors
from logic.clusters_and_titles import clusterize_results, get_cluster_titles
from logic.search import get_search_results, get_full_results_from_meta_info
from logic.local_map_cache import local_maps, vectorize_stage_hash_to_map_id, \
    projection_stage_hash_to_map_id, get_map_parameters_hash, get_search_stage_hash, \
    get_vectorize_stage_hash, get_projection_stage_hash


ABSCLUST_SCHEMA_ID = 1

default_map_data = {
    "last_accessed": None,
    "finished": False,
    "errors": [],
    "is_stored": False,
    "parameters": {
            # schema_id
            # search settings
            # vectorize settings
            # projection settings
            # render settings
        },
    "last_parameters": {},
    "progress": {
        "total_steps": 1,
        "current_step": 0,
        "step_title": "Preparation",
        "projections_available": False,
    },
    "map_rendering": None,
    "results": {
        "search_result_meta_information": {},
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


def get_or_create_map(params, ignore_cache):
    map_id = get_map_parameters_hash(params)

    if map_id not in local_maps and not ignore_cache:
        map_data = get_stored_map_data(map_id)
        if map_data:
            local_maps[map_id] = map_data

    if map_id not in local_maps or ignore_cache:
        map_data = deepcopy(default_map_data)
        map_data['last_accessed'] = time.time()
        map_data['parameters'] = params

        local_maps[map_id] = map_data
        thread = Thread(target = generate_map, args = (map_id, ignore_cache))
        thread.start()

    return map_id


def generate_map(map_id, ignore_cache):
    timings = Timings()

    map_data = local_maps[map_id]
    params = DotDict(map_data["parameters"])

    # we already know there is no other exactly equal map,
    # now check if there are maps that are partially equal:
    found_similar_map = False
    projection_stage_params_hash = get_projection_stage_hash(params)
    vectorize_stage_params_hash = get_vectorize_stage_hash(params)
    maps_with_same_projection = projection_stage_hash_to_map_id.get(projection_stage_params_hash, [])
    similar_map = None
    for similar_map_id in maps_with_same_projection:
        if similar_map_id in local_maps:
            similar_map = local_maps[similar_map_id]
            map_data['last_parameters'] = similar_map['parameters']
            found_similar_map = True
            break
    if not found_similar_map:
        maps_with_same_vectorization = vectorize_stage_hash_to_map_id.get(vectorize_stage_params_hash, [])
        for similar_map_id in maps_with_same_vectorization:
            if similar_map_id in local_maps:
                similar_map = local_maps[similar_map_id]
                map_data['last_parameters'] = similar_map['parameters']
                found_similar_map = True
                break

    origin_map: dict | None = None
    if params.search.search_type == 'cluster':
        origin_map_id: str = params.search.cluster_origin_map_id

        if origin_map_id not in local_maps:
            map_data['errors'].append("Origin map of this cluster doesn't exist anymore")
            return

        origin_map = local_maps[origin_map_id]
        assert origin_map is not None  # to tell pylance that this is definitely not None
        map_data['results']['w2v_embeddings_file_path'] = origin_map['results']['w2v_embeddings_file_path']
        map_data['results']['texture_atlas_path'] = origin_map['results']['texture_atlas_path']

    schema_id = params.schema_id
    schema = get_object_schema(schema_id)
    map_data["hover_label_rendering"] = schema.hover_label_rendering
    timings.log("map preparation")

    map_vector_field = params.vectorize.map_vector_field
    texture_atlas_thread = None
    search_results = None

    search_phase_is_needed = not similar_map or vectorize_stage_params_hash != get_vectorize_stage_hash(map_data['last_parameters']) or ignore_cache

    if not search_phase_is_needed:
        assert similar_map is not None
        logging.warning("reusing search stage results")
        map_data["results"]["search_result_meta_information"] = deepcopy(similar_map["results"]["search_result_meta_information"])
        map_data['results']['search_result_score_info'] = deepcopy(similar_map['results']['search_result_score_info'])
        map_data["results"]["texture_atlas_path"] = deepcopy(similar_map["results"].get("texture_atlas_path"))
        map_data["results"]["per_point_data"]["item_ids"] = deepcopy(similar_map["results"]["per_point_data"]["item_ids"])
        map_data["results"]["per_point_data"]["hover_label_data"] = deepcopy(similar_map["results"]["per_point_data"]["hover_label_data"])
        search_result_meta_information = map_data['results']['search_result_meta_information']
        search_results = get_full_results_from_meta_info(schema, params.vectorize, search_result_meta_information, 'map', timings)
        timings.log("reusing vectorize stage results")
    else:
        map_data['progress']['step_title'] = "Getting search results"
        params_str = json.dumps(map_data["parameters"], indent=2)
        search_results_all = get_search_results(params_str, purpose='map', timings=timings)
        search_results = search_results_all['items']
        map_data['results']['search_result_score_info'] = search_results_all['score_info']

        if not search_results:
            map_data["errors"].append("No results found")
            map_data["results"]["timings"] = timings.get_timestamps()
            map_data["finished"] = True
            return

        timings.log("database query")

        # texture atlas:
        thumbnail_field = schema.thumbnail_image
        if thumbnail_field:
            search_params_hash = get_search_stage_hash(params)
            atlas_filename = f"map_data/atlas_{search_params_hash}.jpg"
            if not os.path.exists(atlas_filename):
                def generate_texture_atlas():
                    atlas_total_width = 4096
                    sprite_size = params.search.get("thumbnail_sprite_size", 64)
                    max_images = pow(atlas_total_width // sprite_size, 2)
                    atlas = Image.new("RGB", (atlas_total_width, atlas_total_width))
                    for i, item in enumerate(search_results[:max_images]):
                        if item.get(thumbnail_field, None) and os.path.exists(item[thumbnail_field]):
                            image = Image.open(item[thumbnail_field])
                            image.thumbnail((sprite_size, sprite_size))
                            image = image.resize((sprite_size, sprite_size))
                            imagesPerLine = (atlas_total_width / sprite_size)
                            posRow: int = int(i / imagesPerLine)
                            posCol: int = int(i % imagesPerLine)
                            atlas.paste(image, (posCol * sprite_size, posRow * sprite_size))
                            image.close()
                        else:
                            logging.warning(f"Image file doesn't exist: {item.get(thumbnail_field, None)}")
                    atlas.save(atlas_filename, quality=80)
                    map_data["results"]["texture_atlas_path"] = atlas_filename

                texture_atlas_thread = Thread(target=generate_texture_atlas)
                texture_atlas_thread.start()
            else:
                map_data["results"]["texture_atlas_path"] = atlas_filename

        map_data["results"]["per_point_data"]["item_ids"] = [item["_id"] for item in search_results]

        hover_label_data_total = []
        for item in search_results:
            hover_label_data = {}
            hover_label_data['_id'] = item['_id']
            for field in schema.hover_label_rendering.required_fields:
                hover_label_data[field] = item.get(field, None)
            hover_label_data_total.append(hover_label_data)

        map_data["results"]["per_point_data"]["hover_label_data"] = hover_label_data_total

    assert search_results is not None
    all_map_vectors_present = all([item.get(params.vectorize.map_vector_field) is not None for item in search_results])
    projection_phase_is_needed = not similar_map or projection_stage_params_hash != get_projection_stage_hash(map_data['last_parameters']) or ignore_cache
    adding_missing_vectors_is_needed = search_phase_is_needed or (projection_phase_is_needed and not all_map_vectors_present)

    if adding_missing_vectors_is_needed:
        query = params.search.all_field_query
        # TODO: query might be something else when using separate queries etc.
        if params.search.search_type == 'cluster' and origin_map is not None:
            query = origin_map['parameters']['search']['all_field_query']
        if map_vector_field == "w2v_vector":
            add_w2v_vectors(search_results, query, params, schema.descriptive_text_fields, map_data, vectorize_stage_params_hash, timings)
        elif schema.object_fields[params.vectorize.map_vector_field].generator \
                and not all_map_vectors_present:
            add_missing_map_vectors(search_results, query, params, map_data, schema, timings)

        search_result_meta_information = {}
        for item in search_results:
            search_result_meta_information[item['_id']] = {
                field: item[field] for field in ['_id', '_origins', '_score', '_reciprocal_rank_score']
            }
        map_data['results']['search_result_meta_information'] = search_result_meta_information

    projection_parameters = params.get("projection", {})
    scores = [e["_score"] for e in search_results]
    map_data["results"]["per_point_data"]["scores"] = scores
    point_sizes = [e.get(params.rendering.point_size) for e in search_results] if params.rendering.point_size != 'equal' else [1] * len(search_results)
    map_data["results"]["per_point_data"]["point_sizes"] = point_sizes

    if not projection_phase_is_needed:
        assert similar_map is not None
        logging.warning("reusing projection stage results")
        projections = similar_map["results"]["per_point_data"]["raw_projections"]
        map_data["results"]["per_point_data"]["positions_x"] = similar_map["results"]["per_point_data"]["positions_x"]
        map_data["results"]["per_point_data"]["positions_y"] = similar_map["results"]["per_point_data"]["positions_y"]
        positions = np.column_stack([map_data["results"]["per_point_data"]["positions_x"], map_data["results"]["per_point_data"]["positions_y"]])
        map_data["progress"]["embeddings_available"] = True
        timings.log("reusing projection stage results")
    else:
        vectors = np.asarray([e[map_vector_field] for e in search_results])  # shape result_count x 768
        timings.log("convert to numpy")

        def on_umap_progress(working_in_embedding_space, current_iteration, total_iterations, projections):
            map_data["progress"] = {
                "total_steps": total_iterations,
                "current_step": current_iteration,
                "step_title": "UMAP 2/2: finetuning" if working_in_embedding_space else "UMAP 1/2: pair-wise distances",
                "embeddings_available": working_in_embedding_space,
            }

            if working_in_embedding_space and projections is not None:
                if projection_parameters.get("shape") == "1d_plus_distance_polar":
                    projections = np.column_stack(polar_to_cartesian(1 - normalize_array(scores), normalize_array(projections[:, 0]) * np.pi * 2))

                map_data["results"]["per_point_data"]["positions_x"] = projections[:, 0].tolist()
                map_data["results"]["per_point_data"]["positions_y"] = projections[:, 1].tolist()

        # Note: UMAP computes all distance pairs when less than 4096 points and uses approximation above
        # Progress might only be available below 4096

        map_data['progress']['step_title'] = "UMAP Preparation"
        target_dimensions = 1 if projection_parameters.get("shape") == "1d_plus_distance_polar" else 2
        import umap  # import it only when needed as it slows down the startup time
        umap_task = umap.UMAP(n_components=target_dimensions, random_state=99,
                              min_dist=projection_parameters.get("min_dist", 0.05),
                              n_epochs=projection_parameters.get("n_epochs", 500),
                              n_neighbors=projection_parameters.get("n_neighbors", 15),
                              metric=projection_parameters.get("metric", "euclidean"),
                              )
        projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)
        map_data["results"]["per_point_data"]["raw_projections"] = projections.tolist()
        if projection_parameters.get("shape") == "1d_plus_distance_polar":
            positions = np.column_stack(polar_to_cartesian(1 - normalize_array(scores), normalize_array(projections[:, 0]) * np.pi * 2))
        elif projection_parameters.get("shape") == "score_graph":
            positions = np.column_stack([[float(x) / len(scores) for x in range(len(scores))], normalize_array(scores)])
        else:
            positions = projections
        map_data["results"]["per_point_data"]["positions_x"] = positions[:, 0].tolist()
        map_data["results"]["per_point_data"]["positions_y"] = positions[:, 1].tolist()
        map_data["progress"]["embeddings_available"] = True
        timings.log("UMAP fit transform")

    run_clusterize_and_render_stage = True  # just to label this stage
    if run_clusterize_and_render_stage:
        map_data['progress']['step_title'] = "Clusterize results"
        cluster_id_per_point = clusterize_results(projections, params.rendering.clusterizer_parameters)
        map_data["results"]["per_point_data"]["cluster_ids"] = cluster_id_per_point.tolist()
        timings.log("clustering")

        map_data['progress']['step_title'] = "Find cluster titles"
        cluster_data = get_cluster_titles(cluster_id_per_point, positions, search_results, schema.descriptive_text_fields, timings)
        timings.log("cluster title")

        map_data["results"]["clusters"] = cluster_data

    if texture_atlas_thread:
        texture_atlas_thread.join()
        timings.log("generating texture atlas")

    map_data["results"]["timings"] = timings.get_timestamps()
    map_data["finished"] = True

    # adding this map to the partial map caches:
    vectorize_stage_hash_to_map_id[vectorize_stage_params_hash].append(map_id)
    projection_stage_hash_to_map_id[projection_stage_params_hash].append(map_id)


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
