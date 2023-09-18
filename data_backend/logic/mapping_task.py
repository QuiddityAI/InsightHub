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

from logic.add_vectors import add_vectors_to_results
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


def get_or_create_map(params):
    map_id = get_map_parameters_hash(params)

    if map_id not in local_maps:
        map_data = get_stored_map_data(map_id)
        if map_data:
            local_maps[map_id] = map_data
        else:
            map_data = deepcopy(default_map_data)
            map_data['last_accessed'] = time.time()
            map_data['parameters'] = params

            local_maps[map_id] = map_data
            thread = Thread(target = generate_map, args = (map_id,))
            thread.start()

    return map_id


def generate_map(map_id):
    timings = Timings()

    map_data = local_maps[map_id]
    params = DotDict(map_data["parameters"])

    # we already know there is no other exactly equal map,
    # now check if there are maps that are partially equal:
    found_similar_map = False
    projection_stage_params_hash = get_projection_stage_hash(params)
    vectorize_stage_params_hash = get_vectorize_stage_hash(params)
    maps_with_same_projection = projection_stage_hash_to_map_id.get(projection_stage_params_hash, [])
    for similar_map_id in maps_with_same_projection:
        if similar_map_id in local_maps:
            similar_map = local_maps[similar_map_id]
            map_data['results'] = similar_map['results']
            map_data['last_parameters'] = similar_map['parameters']
            found_similar_map = True
            break
    if not found_similar_map:
        maps_with_same_vectorization = vectorize_stage_hash_to_map_id.get(vectorize_stage_params_hash, [])
        for similar_map_id in maps_with_same_vectorization:
            if similar_map_id in local_maps:
                similar_map = local_maps[similar_map_id]
                map_data['results'] = similar_map['results']
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

    map_vector_field = params.vectorize.map_vector_field
    schema_id = params.schema_id
    schema = get_object_schema(schema_id)
    map_data["hover_label_rendering"] = schema.hover_label_rendering
    timings.log("preparation")

    texture_atlas_thread = None
    if vectorize_stage_params_hash == get_vectorize_stage_hash(map_data['last_parameters']):
        logging.warning("reusing vectorize stage results")
        search_result_meta_information = map_data['results']['search_result_meta_information']
        search_results = get_full_results_from_meta_info(schema, params.search, params.vectorize, search_result_meta_information, 'map')
    else:
        map_data['progress']['step_title'] = "Getting search results"
        params_str = json.dumps(map_data["parameters"], indent=2)
        search_results = get_search_results(params_str, purpose='map', timings=timings)['items']

        if not search_results:
            map_data["errors"].append("No results found")
            map_data["results"]["timings"] = timings.get_timestamps()
            map_data["finished"] = True
            return

        search_result_meta_information = {}
        for item in search_results:
            search_result_meta_information[item['_id']] = {
                field: item[field] for field in ['_id', '_origins', '_score', '_reciprocal_rank_score']
            }
        map_data['results']['search_result_meta_information'] = search_result_meta_information

        timings.log("database query")

        # texture atlas:
        thumbnail_field = schema.thumbnail_image
        if thumbnail_field:
            search_params_hash = get_search_stage_hash(params)
            atlas_filename = f"map_data/atlas_{search_params_hash}.png"
            if not os.path.exists(atlas_filename):
                def generate_texture_atlas():
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
                    atlas.save(atlas_filename)
                    map_data["results"]["texture_atlas_path"] = atlas_filename

                texture_atlas_thread = Thread(target=generate_texture_atlas)
                texture_atlas_thread.run()
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

        # eventually, the vectors should come directly from the database
        # but for the AbsClust database, the vectors need to be added on-demand:
        if schema.id == ABSCLUST_SCHEMA_ID:
            map_data['progress']['step_title'] = "Generating vectors"
            query = params.search.all_field_query
            if params.search.search_type == 'cluster' and origin_map is not None:
                query = origin_map['parameters']['search']['all_field_query']
            add_vectors_to_results(search_results, query, params, schema.descriptive_text_fields, map_data, timings)


    projection_parameters = params.get("projection", {})
    scores = [e["_score"] for e in search_results]
    map_data["results"]["per_point_data"]["scores"] = scores
    point_sizes = [e.get(params.rendering.point_size_field) for e in search_results] if params.rendering.point_size_field != 'equal' else [1] * len(search_results)
    map_data["results"]["per_point_data"]["point_sizes"] = point_sizes

    if projection_stage_params_hash == get_projection_stage_hash(map_data['last_parameters']):
        logging.warning("reusing projection stage results")
        projections = np.column_stack([map_data["results"]["per_point_data"]["positions_x"], map_data["results"]["per_point_data"]["positions_y"]])
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
        umap_task = umap.UMAP(n_components=target_dimensions, random_state=99, min_dist=projection_parameters.get("min_dist", 0.05), n_epochs=projection_parameters.get("n_epochs", 500))
        projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)
        map_data["results"]["per_point_data"]["positions_x"] = projections[:, 0].tolist()
        map_data["results"]["per_point_data"]["positions_y"] = projections[:, 1].tolist()
        timings.log("UMAP fit transform")

    run_clusterize_and_render_stage = True  # just to label this stage
    if run_clusterize_and_render_stage:
        map_data['progress']['step_title'] = "Clusterize results"
        cluster_id_per_point = clusterize_results(projections)
        timings.log("clustering")

        if projection_parameters.get("shape") == "1d_plus_distance_polar":
            projections = np.column_stack(polar_to_cartesian(1 - normalize_array(scores), normalize_array(projections[:, 0]) * np.pi * 2))

        map_data["results"]["per_point_data"]["cluster_ids"] = cluster_id_per_point.tolist()

        map_data['progress']['step_title'] = "Find cluster titles"
        cluster_data = get_cluster_titles(cluster_id_per_point, projections, search_results, schema.descriptive_text_fields, timings)
        timings.log("cluster title")

        map_data["results"]["clusters"] = cluster_data

    if texture_atlas_thread:
        texture_atlas_thread.join()
        timings.log("generating texture atlas")

    map_data["results"]["timings"] = timings.get_timestamps()
    map_data["finished"] = True

    # adding this map to the partial map caches:
    vectorize_stage_hash_to_map_id[projection_stage_params_hash].append(map_id)
    projection_stage_hash_to_map_id[vectorize_stage_params_hash].append(map_id)


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
