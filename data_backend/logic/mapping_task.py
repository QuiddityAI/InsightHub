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
from utils.helpers import normalize_array, polar_to_cartesian, get_vector_field_dimensions
from utils.dotdict import DotDict

from database_client.django_client import get_dataset, get_stored_map_data

from logic.add_vectors import add_missing_map_vectors, add_w2v_vectors
from logic.clusters_and_titles import clusterize_results, get_cluster_titles
from logic.search import get_search_results, get_full_results_from_meta_info
from logic.search_common import fill_in_details_from_text_storage_list
from logic.local_map_cache import local_maps, vectorize_stage_hash_to_map_id, \
    projection_stage_hash_to_map_id, get_map_parameters_hash, get_search_stage_hash, \
    get_vectorize_stage_hash, get_projection_stage_hash
from logic.thumbnail_atlas import generate_thumbnail_atlas, THUMBNAIL_ATLAS_DIR


ABSCLUST_DATASET_ID = 1

default_map_data = {
    "last_accessed": None,
    "finished": False,
    "errors": [],
    "is_stored": False,
    "parameters": {
            # dataset_id
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
            "size": [],  # same for hue, sat, val, opacity and secondary values
        },
        "clusters": {
            # x: { id: x, title: foo, centerX, centerY }, for each cluster
        },
        "thumbnail_atlas_filename": None,
        "thumbnail_sprite_size": None,
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
        map_data['results']['thumbnail_atlas_filename'] = origin_map['results']['thumbnail_atlas_filename']
        map_data['results']['thumbnail_sprite_size'] = origin_map['results']['thumbnail_sprite_size']

    # TODO: support multiple datasets, this is just a workaround to make it work with one again
    dataset_id = params.dataset_ids[0]
    dataset = get_dataset(dataset_id)
    timings.log("map preparation")

    map_vector_field = params.vectorize.map_vector_field
    thumbnail_atlas_thread = None
    search_results = None

    search_phase_is_needed = not similar_map or vectorize_stage_params_hash != get_vectorize_stage_hash(map_data['last_parameters']) or ignore_cache

    if not search_phase_is_needed:
        assert similar_map is not None
        logging.warning("reusing search stage results")
        map_data["results"]["search_result_meta_information"] = deepcopy(similar_map["results"]["search_result_meta_information"])
        map_data['results']['search_result_score_info'] = deepcopy(similar_map['results']['search_result_score_info'])
        map_data["results"]["thumbnail_atlas_filename"] = deepcopy(similar_map["results"].get("thumbnail_atlas_filename"))
        map_data["results"]["thumbnail_sprite_size"] = deepcopy(similar_map["results"].get("thumbnail_sprite_size"))
        map_data["results"]["per_point_data"]["item_ids"] = deepcopy(similar_map["results"]["per_point_data"]["item_ids"])
        map_data["results"]["per_point_data"]["hover_label_data"] = deepcopy(similar_map["results"]["per_point_data"]["hover_label_data"])
        search_result_meta_information = map_data['results']['search_result_meta_information']
        search_results = get_full_results_from_meta_info(dataset, params.vectorize, search_result_meta_information, 'map', timings)
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

        # thumbnail atlas:
        thumbnail_field = dataset.thumbnail_image
        if thumbnail_field:
            search_params_hash = get_search_stage_hash(params)
            sprite_size = params.search.get("thumbnail_sprite_size", "auto")
            if sprite_size == "auto":
                if len(search_results) <= pow(4096 / 256, 2):
                    sprite_size = 256
                elif len(search_results) <= pow(4096 / 128, 2):
                    sprite_size = 128
                else:
                    sprite_size = 64
            map_data["results"]["thumbnail_sprite_size"] = sprite_size
            atlas_filename = f"atlas_{search_params_hash}.webp"
            atlas_path = os.path.join(THUMBNAIL_ATLAS_DIR, atlas_filename)
            if os.path.exists(atlas_path) and not ignore_cache:
                map_data["results"]["thumbnail_atlas_filename"] = atlas_filename
            else:
                # don't leave the field empty, otherwise the last atlas is still visible
                map_data["results"]["thumbnail_atlas_filename"] = "loading"
                thumbnail_uris = [item.get(thumbnail_field, None) for item in search_results]
                def _generate_thumbnail_atlas():
                    t1 = time.time()
                    def _on_success():
                        map_data["results"]["thumbnail_atlas_filename"] = atlas_filename
                    generate_thumbnail_atlas(atlas_path, thumbnail_uris, sprite_size, _on_success)
                    time_to_generate_atlas = time.time() - t1
                    timings.timings.append({"part": "thumbnail atlas generation", "duration": time_to_generate_atlas})

                thumbnail_atlas_thread = Thread(target=_generate_thumbnail_atlas)
                thumbnail_atlas_thread.start()

        map_data["results"]["per_point_data"]["item_ids"] = [item["_id"] for item in search_results]

        hover_label_data_total = []
        for item in search_results:
            hover_label_data = {}
            hover_label_data['_id'] = item['_id']
            hover_label_data['_dataset_id'] = item['_dataset_id']
            hover_label_data['_score'] = item['_score']
            hover_label_data['_reciprocal_rank_score'] = item['_reciprocal_rank_score']
            hover_label_data['_origins'] = item['_origins']
            for field in dataset.hover_label_rendering.required_fields:
                hover_label_data[field] = item.get(field, None)
            hover_label_data_total.append(hover_label_data)

        map_data["results"]["per_point_data"]["hover_label_data"] = hover_label_data_total

    assert search_results is not None
    all_map_vectors_present = all([item.get(params.vectorize.map_vector_field) is not None for item in search_results])
    projection_phase_is_needed = not similar_map or projection_stage_params_hash != get_projection_stage_hash(map_data['last_parameters']) or ignore_cache
    adding_missing_vectors_is_needed = search_phase_is_needed or (projection_phase_is_needed and not all_map_vectors_present)
    # TODO: decide what to do with secondary_map_vector

    if adding_missing_vectors_is_needed:
        query = params.search.all_field_query
        # TODO: query might be something else when using separate queries etc.
        if params.search.search_type == 'cluster' and origin_map is not None:
            query = origin_map['parameters']['search']['all_field_query']
        if map_vector_field == "w2v_vector":
            add_w2v_vectors(search_results, query, params, dataset.descriptive_text_fields, map_data, vectorize_stage_params_hash, timings)
        elif dataset.object_fields[params.vectorize.map_vector_field].generator \
                and not all_map_vectors_present:
            add_missing_map_vectors(search_results, query, params, map_data, dataset, timings)

        search_result_meta_information = {}
        for item in search_results:
            search_result_meta_information[item['_id']] = {
                field: item[field] for field in ['_id', '_origins', '_score', '_reciprocal_rank_score']
            }
        map_data['results']['search_result_meta_information'] = search_result_meta_information

    projection_parameters = params.projection
    scores = [e["_score"] for e in search_results]
    map_data["results"]["per_point_data"]["scores"] = scores
    scores = np.array(scores)

    if not projection_phase_is_needed:
        assert similar_map is not None
        logging.warning("reusing projection stage results")
        raw_projections = similar_map["results"]["per_point_data"]["raw_projections"]
        map_data["results"]["per_point_data"]["positions_x"] = similar_map["results"]["per_point_data"]["positions_x"]
        map_data["results"]["per_point_data"]["positions_y"] = similar_map["results"]["per_point_data"]["positions_y"]
        final_positions = np.column_stack([map_data["results"]["per_point_data"]["positions_x"], map_data["results"]["per_point_data"]["positions_y"]])
        map_data["progress"]["embeddings_available"] = True
        timings.log("reusing projection stage results")
    else:
        cartesian_positions = np.zeros([len(search_results), 2])
        final_positions = np.zeros([len(search_results), 2])
        if projection_parameters.x_axis.type == "number_field":
            field = projection_parameters.x_axis.parameter
            fill_in_details_from_text_storage_list(dataset.id, search_results, [field])
            cartesian_positions[:, 0] = [e.get(field, -1) for e in search_results]
        elif projection_parameters.x_axis.type == "count":
            cartesian_positions[:, 0] = [len(e.get(projection_parameters.x_axis.parameter, [])) for e in search_results]
        elif projection_parameters.x_axis.type == "rank":
            cartesian_positions[:, 0] = list(range(len(search_results)))
        elif projection_parameters.x_axis.type == "score":
            cartesian_positions[:, 0] = [e.get("_score", 0.0) for e in search_results]
            # TODO: fulltext score
        elif projection_parameters.x_axis.type == "classifier":
            # TODO
            pass
        if projection_parameters.y_axis.type == "number_field":
            field = projection_parameters.y_axis.parameter
            fill_in_details_from_text_storage_list(dataset.id, search_results, [field])
            cartesian_positions[:, 1] = [e.get(field, -1) for e in search_results]
        elif projection_parameters.y_axis.type == "count":
            cartesian_positions[:, 1] = [len(e.get(projection_parameters.y_axis.parameter, [])) for e in search_results]
        elif projection_parameters.y_axis.type == "rank":
            cartesian_positions[:, 1] = list(range(len(search_results)))
        elif projection_parameters.y_axis.type == "score":
            cartesian_positions[:, 1] = [e.get("_score", 0.0) for e in search_results]
            # TODO: fulltext score
        elif projection_parameters.y_axis.type == "classifier":
            # TODO
            pass

        umap_dimensions_required = 0
        if projection_parameters.x_axis.type == "umap" and projection_parameters.y_axis.type == "umap":
            umap_dimensions_required = 2
        elif projection_parameters.x_axis.type == "umap" or projection_parameters.y_axis.type == "umap":
            umap_dimensions_required = 1

        def transform_coordinate_system_and_write_to_map():
            nonlocal cartesian_positions, final_positions
            final_positions = cartesian_positions[:]
            if projection_parameters.invert_x_axis:
                final_positions[:, 0] = 1 - normalize_array(final_positions[:, 0])
            if projection_parameters.use_polar_coordinates:
                final_positions = polar_to_cartesian(1 - normalize_array(final_positions[:, 0]), normalize_array(final_positions[:, 1]) * np.pi * 2)
            map_data["results"]["per_point_data"]["positions_x"] = final_positions[:, 0].tolist()
            map_data["results"]["per_point_data"]["positions_y"] = final_positions[:, 1].tolist()

        if umap_dimensions_required:
            vector_size = 256 if map_vector_field == "w2v_vector" else get_vector_field_dimensions(dataset.object_fields[map_vector_field])
            # in the case the map vector can't be generated (missing images etc.), use a dummy vector:
            dummy_vector = np.zeros(vector_size)
            vectors = np.asarray([e.get(map_vector_field, dummy_vector) for e in search_results])
            timings.log("convert to numpy")

            def apply_projections_to_positions(raw_projections):
                nonlocal cartesian_positions, final_positions
                if projection_parameters.x_axis.type == "umap" and projection_parameters.y_axis.type == "umap":
                    cartesian_positions = raw_projections
                elif projection_parameters.x_axis.type == "umap":
                    cartesian_positions[:, 0] = raw_projections[:, 0]
                else:  # projection_parameters.y_axis.type == "umap"
                    cartesian_positions[:, 1] = raw_projections[:, 0]

            def on_umap_progress(working_in_embedding_space, current_iteration, total_iterations, projections):
                map_data["progress"] = {
                    "total_steps": total_iterations,
                    "current_step": current_iteration,
                    "step_title": "UMAP 2/2: finetuning" if working_in_embedding_space else "UMAP 1/2: pair-wise distances",
                    "embeddings_available": working_in_embedding_space,
                }

                if working_in_embedding_space and projections is not None:
                    apply_projections_to_positions(projections)
                    transform_coordinate_system_and_write_to_map()

            # Note: UMAP computes all distance pairs when less than 4096 points and uses approximation above
            # Progress might only be available below 4096

            map_data['progress']['step_title'] = "UMAP Preparation"
            import umap  # import it only when needed as it slows down the startup time
            umap_task = umap.UMAP(n_components=umap_dimensions_required, random_state=99,
                                min_dist=projection_parameters.get("min_dist", 0.17),
                                n_epochs=projection_parameters.get("n_epochs", 500),
                                n_neighbors=projection_parameters.get("n_neighbors", 15),
                                metric=projection_parameters.get("metric", "euclidean"),
                                )
            raw_projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)  # type: ignore
            map_data["results"]["per_point_data"]["raw_projections"] = raw_projections.tolist()
            apply_projections_to_positions(raw_projections)
            timings.log("UMAP fit transform")
        else:
            # no umap required:
            raw_projections = cartesian_positions

        transform_coordinate_system_and_write_to_map()
        map_data["progress"]["embeddings_available"] = True

    run_clusterize_and_render_stage = True  # just to label this stage
    if run_clusterize_and_render_stage:
        map_data['progress']['step_title'] = "Clusterize results"
        cluster_id_per_point = clusterize_results(raw_projections, params.rendering.clusterizer_parameters)
        map_data["results"]["per_point_data"]["cluster_ids"] = cluster_id_per_point.tolist()
        timings.log("clustering")

        map_data['progress']['step_title'] = "Find cluster titles"
        if dataset.descriptive_text_fields:
            cluster_data = get_cluster_titles(cluster_id_per_point, final_positions, search_results, dataset.descriptive_text_fields, timings)
            map_data["results"]["clusters"] = cluster_data
        else:
            map_data["results"]["clusters"] = {}

        for attr in ["size", "hue", "val", "sat", "opacity", "secondary_hue", "secondary_val", "secondary_sat", "secondary_opacity", "flatness"]:
            attr_type = params.rendering[attr].type
            attr_parameter = params.rendering[attr].parameter
            if attr_type == "number_field":
                field = attr_parameter
                fill_in_details_from_text_storage_list(dataset.id, search_results, [field])
                values = [e.get(field) or 0.0 for e in search_results]
                map_data["results"]["per_point_data"][attr] = values
            elif attr_type == "count":
                map_data["results"]["per_point_data"][attr] = [len(e.get(attr_parameter, [])) for e in search_results]
            elif attr_type == "rank":
                map_data["results"]["per_point_data"][attr] = list(range(len(search_results)))
            elif attr_type == "score":
                values = [e.get("_score") for e in search_results]
                map_data["results"]["per_point_data"][attr] = values
            elif attr_type == "cluster_idx":
                map_data["results"]["per_point_data"][attr] = cluster_id_per_point.tolist()

    if thumbnail_atlas_thread:
        thumbnail_atlas_thread.join()
        timings.log("waiting for thumbnail atlas")

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
