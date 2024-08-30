from collections import defaultdict
from copy import deepcopy
import logging
from threading import Thread
import json
import os
import time

import numpy as np

# import umap  # imported lazily when used

from utils.collect_timings import Timings
from utils.helpers import normalize_array, polar_to_cartesian, get_vector_field_dimensions, get_field_from_all_items
from utils.dotdict import DotDict
from utils.source_plugin_types import SourcePlugin

from database_client.django_client import answer_question_using_items, get_dataset, get_stored_map_data, get_trained_classifier

from logic.add_vectors import add_missing_map_vectors, add_w2v_vectors
from logic.clusters_and_titles import clusterize_results, get_cluster_titles
from logic.search import get_search_results, get_full_results_from_meta_info
from logic.search_common import fill_in_details_from_text_storage
from logic.local_map_cache import local_maps, vectorize_stage_hash_to_map_id, \
    projection_stage_hash_to_map_id, get_map_parameters_hash, get_search_stage_hash, \
    get_vectorize_stage_hash, get_projection_stage_hash, cache_full_item_data, get_cached_full_item_data
from logic.thumbnail_atlas import generate_thumbnail_atlas, THUMBNAIL_ATLAS_DIR
from logic.extract_pipeline import get_pipeline_steps
from logic.generate_missing_values import generate_missing_values_for_given_elements
from logic.classifiers import get_embedding_space_from_ds_and_field


default_map_data = {
    "last_accessed": None,
    "finished": False,
    "errors": [],
    "is_stored": False,
    "parameters": {
            # dataset_ids
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
    "results": {
        "slimmed_items_per_dataset": {},  # dataset_id -> item_id -> data
        "per_point_data": {
            "item_ids": [],  # list of tuples (dataset_id, item_id)
            "scores": [],
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


def get_or_create_map(params, ignore_cache: bool) -> str:
    map_id: str = get_map_parameters_hash(params)

    if map_id not in local_maps and not ignore_cache:
        map_data = get_stored_map_data(map_id)
        if map_data:
            local_maps[map_id] = map_data

    if map_id not in local_maps or ignore_cache:
        map_data = deepcopy(default_map_data)
        map_data['last_accessed'] = time.time()
        map_data['parameters'] = params

        local_maps[map_id] = map_data
        thread = Thread(target = generate_map_safe, args = (map_id, ignore_cache))
        thread.start()

    return map_id


def generate_map_safe(map_id: str, ignore_cache: bool):
    try:
        generate_map(map_id, ignore_cache)
    except Exception as e:
        logging.error(f"Error while generating map {map_id}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        if map_id in local_maps:
            local_maps[map_id]["errors"].append(f"Error while generating map: {e}")
            local_maps[map_id]["finished"] = True
        raise e


def generate_map(map_id: str, ignore_cache: bool):
    timings: Timings = Timings()

    # ----------------- Preparation Phase -----------------

    # map_data was already put in local_maps to store parameters
    # and to make get_map_results work during initial phase:
    map_data: dict = local_maps[map_id]
    params: DotDict = DotDict(map_data["parameters"])
    datasets = {dataset_id: get_dataset(dataset_id) for dataset_id in params.search.dataset_ids}

    # variables set in specific stages but used globally later on:
    thumbnail_atlas_thread = None
    question_thread = None
    sorted_ids: list[tuple[str, str]] = []
    items_by_dataset = {}

    # we already know there is no other exactly equal map,
    # now check if there are maps that are partially equal:
    vectorize_stage_params_hash: str = get_vectorize_stage_hash(params)
    projection_stage_params_hash: str = get_projection_stage_hash(params)
    similar_map: dict | None = find_similar_map(vectorize_stage_params_hash, projection_stage_params_hash)
    if similar_map:
        same_search_and_vectorize_settings = vectorize_stage_params_hash == get_vectorize_stage_hash(similar_map['last_parameters'])
        same_search_vec_and_projection_settings = projection_stage_params_hash == get_projection_stage_hash(similar_map['last_parameters'])
        map_data['last_parameters'] = similar_map['parameters']
    else:
        same_search_and_vectorize_settings = False
        same_search_vec_and_projection_settings = False

    timings.log("map preparation")

    # ----------------- Search / Data Collection Phase -----------------
    # aka collecting the relevant data, not necessarily search

    search_phase_can_be_resused = similar_map and same_search_and_vectorize_settings and not ignore_cache

    if search_phase_can_be_resused:
        assert similar_map is not None
        sorted_ids, items_by_dataset = reuse_search_phase(map_data, similar_map, params, datasets, items_by_dataset, timings)
        timings.log("reused search stage results")
    else:
        sorted_ids, items_by_dataset, thumbnail_atlas_thread = search_phase(map_data, params, datasets, items_by_dataset, timings)
        if not sorted_ids:
            # no results were found, later stages would fail
            return

    cache_full_item_data(items_by_dataset, map_id)
    assert len(sorted_ids)
    assert items_by_dataset != {}


    # ----------------- Optional: Question Answering Phase -----------------

    if params.search.question:
        def _answer_question():
            item_subset = sorted_ids[:5]
            answer = answer_question_using_items(params.search.question, item_subset)
            map_data["results"]["answer"] = answer

        question_thread = Thread(target=_answer_question)
        question_thread.start()


    # ----------------- Vectorize Phase -----------------

    map_vector_field = params.vectorize.map_vector_field
    all_map_vectors_present = all([x is not None for x in get_field_from_all_items(items_by_dataset, sorted_ids, map_vector_field, None)])
    projection_phase_can_be_reused = similar_map and same_search_vec_and_projection_settings and not ignore_cache
    no_vectorization_needed = search_phase_can_be_resused and projection_phase_can_be_reused and all_map_vectors_present
    # TODO: decide what to do with secondary_map_vector

    if not no_vectorization_needed:
        add_missing_vectors(map_data, params, datasets, items_by_dataset, similar_map, vectorize_stage_params_hash, all_map_vectors_present, timings)

    # scores should be part of the first phase, but might change when new vectors are generated and used for scoring
    scores = get_field_from_all_items(items_by_dataset, sorted_ids, "_score", 0.0)
    map_data["results"]["per_point_data"]["scores"] = scores

    # ----------------- Projection Phase -----------------

    if projection_phase_can_be_reused:
        assert similar_map is not None
        logging.warning("reusing projection stage results")
        raw_projections, final_positions = reuse_projection_phase(map_data, similar_map)
        timings.log("reusing projection stage results")
    else:
        raw_projections, final_positions = projection_phase(map_data, params, datasets, items_by_dataset, sorted_ids, timings)

    # ----------------- Clusterize and Render Phase -----------------

    clusterize_and_render_phase(map_data, params, datasets, items_by_dataset, sorted_ids, raw_projections, final_positions, timings)

    # ----------------- Final Phase -----------------

    if thumbnail_atlas_thread:
        thumbnail_atlas_thread.join()
        timings.log("waiting for thumbnail atlas")

    if question_thread:
        question_thread.join()
        timings.log("waiting for question answering")

    map_data["results"]["timings"] = timings.get_timestamps()
    map_data["finished"] = True

    # adding this map to the partial map caches:
    vectorize_stage_hash_to_map_id[vectorize_stage_params_hash].append(map_id)
    projection_stage_hash_to_map_id[projection_stage_params_hash].append(map_id)


def find_similar_map(vectorize_stage_params_hash: str, projection_stage_params_hash: str) -> dict | None:
    # finding a map with the same vectorization or projection settings:
    maps_with_same_projection: list = projection_stage_hash_to_map_id.get(projection_stage_params_hash, [])
    for similar_map_id in maps_with_same_projection:
        if similar_map_id in local_maps:
            return local_maps[similar_map_id]
    maps_with_same_vectorization = vectorize_stage_hash_to_map_id.get(vectorize_stage_params_hash, [])
    for similar_map_id in maps_with_same_vectorization:
        if similar_map_id in local_maps:
            return local_maps[similar_map_id]


def search_phase(map_data: dict, params: DotDict, datasets: dict, items_by_dataset: dict, timings: Timings) -> tuple[list[tuple[str, str]], dict, Thread | None]:
    map_data['progress']['step_title'] = "Getting search results"
    params_str = json.dumps(map_data["parameters"], indent=2)
    search_results_all = get_search_results(params_str, purpose='map', timings=timings)
    sorted_ids = search_results_all['sorted_ids']
    items_by_dataset = search_results_all['items_by_dataset']
    map_data['results']['search_result_score_info'] = search_results_all['score_info']
    map_data['results']['total_matches'] = search_results_all['total_matches']
    timings.log("database query")

    if not sorted_ids:
        map_data["errors"].append("No results found")
        map_data["results"]["timings"] = timings.get_timestamps()
        map_data["finished"] = True
        return sorted_ids, items_by_dataset, None

    map_data["results"]["per_point_data"]["item_ids"] = sorted_ids

    # currently, thumbnail phase might add missing fields, so do it before collecting the initially transfered data:
    thumbnail_thread = thumbnail_phase(datasets, items_by_dataset, map_data, params, sorted_ids, timings)

    # items_per_dataset contains all data that is needed either here in the backend or in the frontend,
    # but transfering everything might be slow and not all of it is needed initially,
    # so we extract the initially needed data and basically remove the large fields like long texts and vectors:
    slimmed_items_per_dataset = defaultdict(dict)
    generic_fields = {"_id", "_dataset_id", "_score", "_reciprocal_rank_score", "_origins", '_relevant_parts'}
    for ds_id, ds_items in items_by_dataset.items():
        ds_specific_fields = set(datasets[ds_id].schema.hover_label_rendering.required_fields)
        ds_specific_fields |= set(datasets[ds_id].get('schema', {}).get("statistics", {}).get("required_fields", []))
        all_fields = generic_fields | ds_specific_fields
        for item_id, item in ds_items.items():
            slimmed_items_per_dataset[ds_id][item_id] = {field: item.get(field, None) for field in all_fields}

    map_data["results"]["slimmed_items_per_dataset"] = slimmed_items_per_dataset
    if any(dataset.source_plugin == SourcePlugin.BING_WEB_API for dataset in datasets.values()):
        # results from some source types are unique each time or hard to retrieve,
        # those are then stored here in the map_data so that they can be retrieved from there
        # for reclustering or other purposes
        map_data["results"]["full_items_per_dataset"] = items_by_dataset
    return sorted_ids, items_by_dataset, thumbnail_thread


def thumbnail_phase(datasets, items_by_dataset, map_data, params, sorted_ids, timings: Timings):
    if not any([datasets[ds_id].schema.thumbnail_image for ds_id in datasets]):
        return

    for ds_id, dataset in datasets.items():
        if not dataset.schema.thumbnail_image:
            continue
        if dataset.schema.object_fields[dataset.schema.thumbnail_image].generator:
            elements = []
            for item in items_by_dataset[ds_id].values():
                if item.get(dataset.schema.thumbnail_image) is None:
                    elements.append(item)
            pipeline_steps, required_fields, _ = get_pipeline_steps(dataset, only_fields=[dataset.schema.thumbnail_image])
            generate_missing_values_for_given_elements(pipeline_steps, elements)
            logging.info(f"Generated {len(elements)} missing thumbnail URLs")

    search_params_hash = get_search_stage_hash(params)
    sprite_size = params.search.get("thumbnail_sprite_size", "auto")
    if sprite_size == "auto":
        if len(sorted_ids) <= pow(4096 / 256, 2):
            sprite_size = 256
        elif len(sorted_ids) <= pow(4096 / 128, 2):
            sprite_size = 128
        else:
            sprite_size = 64
    map_data["results"]["thumbnail_sprite_size"] = sprite_size
    atlas_filename = f"atlas_{search_params_hash}.webp"
    atlas_path = os.path.join(THUMBNAIL_ATLAS_DIR, atlas_filename)
    # don't leave the field empty, otherwise the last atlas is still visible
    map_data["results"]["thumbnail_atlas_filename"] = "loading"
    thumbnail_uris = [items_by_dataset[ds_id][item_id][datasets[ds_id].schema.thumbnail_image] if datasets[ds_id].schema.thumbnail_image else None for (ds_id, item_id) in sorted_ids]
    def _generate_thumbnail_atlas():
        t1 = time.time()
        aspect_ratios = generate_thumbnail_atlas(atlas_path, thumbnail_uris, sprite_size)
        map_data["results"]["thumbnail_atlas_filename"] = atlas_filename
        map_data["results"]["per_point_data"]["thumbnail_aspect_ratios"] = aspect_ratios
        time_to_generate_atlas = time.time() - t1
        timings.timings.append({"part": "thumbnail atlas generation", "duration": time_to_generate_atlas})

    thumbnail_atlas_thread = Thread(target=_generate_thumbnail_atlas)
    thumbnail_atlas_thread.start()
    return thumbnail_atlas_thread


def reuse_search_phase(map_data: dict, similar_map: dict, params: DotDict, datasets: dict, items_by_dataset: dict, timings: Timings) -> tuple[list[tuple[str, str]], dict]:
    logging.warning("reusing search stage results")
    # copy the search stage results from the similar map to the current map:
    map_data['results']['search_result_score_info'] = deepcopy(similar_map['results']['search_result_score_info'])
    map_data['results']['total_matches'] = deepcopy(similar_map['results']['total_matches'])
    map_data["results"]["thumbnail_atlas_filename"] = deepcopy(similar_map["results"].get("thumbnail_atlas_filename"))
    map_data["results"]["thumbnail_sprite_size"] = deepcopy(similar_map["results"].get("thumbnail_sprite_size"))
    map_data["results"]["per_point_data"]["thumbnail_aspect_ratios"] = deepcopy(similar_map["results"].get("per_point_data", {}).get("thumbnail_aspect_ratios"))
    map_data["results"]["per_point_data"]["item_ids"] = deepcopy(similar_map["results"]["per_point_data"]["item_ids"])
    map_data["results"]["slimmed_items_per_dataset"] = deepcopy(similar_map["results"]["slimmed_items_per_dataset"])
    # extract variables needed for later stages:
    slimmed_items_per_dataset = map_data['results']['slimmed_items_per_dataset']
    sorted_ids = map_data["results"]["per_point_data"]["item_ids"]
    for ds_id, ds_items in slimmed_items_per_dataset.items():
        dataset = datasets[ds_id]
        _, ds_full_items = get_full_results_from_meta_info(dataset, params.vectorize, ds_items, 'map', timings)
        items_by_dataset[ds_id] = ds_full_items
    return sorted_ids, items_by_dataset


def add_missing_vectors(map_data: dict, params: DotDict, datasets: dict, items_by_dataset: dict, similar_map: dict | None, vectorize_stage_params_hash: str, all_map_vectors_present: bool, timings: Timings):
    query = params.search.all_field_query
    # TODO: query might be something else when using separate queries etc.
    origin_map = None
    if params.search.search_type == 'cluster' or params.search.search_type == 'map_subset':
        origin_map_id: str = params.search.cluster_origin_map_id

        if origin_map_id not in local_maps:
            map_data['errors'].append("Origin map of this cluster doesn't exist anymore")
            return

        origin_map = local_maps[origin_map_id]
        assert origin_map is not None  # to tell pylance that this is definitely not None
        map_data['results']['w2v_embeddings_file_path'] = origin_map['results']['w2v_embeddings_file_path']
        query = origin_map['parameters']['search']['all_field_query']
    if params.vectorize.map_vector_field == "w2v_vector":
        # FIXME: w2v vectors need to be generated for all datasets together
        for ds_id, ds_items in items_by_dataset.items():
            dataset = datasets[ds_id]
            add_w2v_vectors(ds_items, query, similar_map, origin_map, dataset.schema.descriptive_text_fields, map_data, vectorize_stage_params_hash, timings)
    elif not all_map_vectors_present:
        for ds_id, ds_items in items_by_dataset.items():
            dataset = datasets[ds_id]
            if dataset.schema.object_fields[params.vectorize.map_vector_field].generator:
                add_missing_map_vectors(ds_items, query, params, map_data, dataset, timings)

    # update slimmed_items_per_dataset because the scores might have changed / were added:
    # FIXME: at this point, the slimmed items are already transfered and won't be updated
    # Where is the score read from slimmed items anyway?
    for ds_id, ds_item in map_data['results']['slimmed_items_per_dataset'].items():
        for item_id, item in ds_item.items():
            item['_score'] = items_by_dataset[ds_id][item_id]['_score']


def projection_phase(map_data: dict, params: DotDict, datasets: dict, items_by_dataset: dict, sorted_ids: list[tuple[str, str]], timings: Timings) -> tuple[np.ndarray, np.ndarray]:
    projection_parameters = params.projection
    cartesian_positions = np.zeros([len(sorted_ids), 2])
    final_positions = np.zeros([len(sorted_ids), 2])
    if projection_parameters.x_axis.type == "number_field":
        field = projection_parameters.x_axis.parameter
        for ds_id, ds_items in items_by_dataset.items():
            fill_in_details_from_text_storage(datasets[ds_id], ds_items, [field])
        cartesian_positions[:, 0] = get_field_from_all_items(items_by_dataset, sorted_ids, field, -1)
    elif projection_parameters.x_axis.type == "count":
        cartesian_positions[:, 0] = [len(v) for v in get_field_from_all_items(items_by_dataset, sorted_ids, projection_parameters.x_axis.parameter, [])]
    elif projection_parameters.x_axis.type == "rank":
        cartesian_positions[:, 0] = list(range(len(sorted_ids)))
    elif projection_parameters.x_axis.type == "score":
        cartesian_positions[:, 0] = get_field_from_all_items(items_by_dataset, sorted_ids, "_score", 0.0)
        # TODO: fulltext score
    elif projection_parameters.x_axis.type == "classifier":
        # TODO
        pass
    if projection_parameters.y_axis.type == "number_field":
        field = projection_parameters.y_axis.parameter
        for ds_id, ds_items in items_by_dataset.items():
            fill_in_details_from_text_storage(datasets[ds_id], ds_items, [field])
        cartesian_positions[:, 1] = get_field_from_all_items(items_by_dataset, sorted_ids, field, -1)
    elif projection_parameters.y_axis.type == "count":
        cartesian_positions[:, 1] = [len(v) for v in get_field_from_all_items(items_by_dataset, sorted_ids, projection_parameters.y_axis.parameter, [])]
    elif projection_parameters.y_axis.type == "rank":
        cartesian_positions[:, 1] = list(range(len(sorted_ids)))
    elif projection_parameters.y_axis.type == "score":
        cartesian_positions[:, 1] = get_field_from_all_items(items_by_dataset, sorted_ids, "_score", 0.0)
        # TODO: fulltext score
    elif projection_parameters.y_axis.type == "classifier":
        # TODO
        pass

    reduced_dimensions_required = 0
    if projection_parameters.x_axis.type == "embedding" and projection_parameters.y_axis.type == "embedding":
        reduced_dimensions_required = 2
    elif projection_parameters.x_axis.type == "embedding" or projection_parameters.y_axis.type == "embedding":
        reduced_dimensions_required = 1

    def transform_coordinate_system_and_write_to_map():
        nonlocal cartesian_positions, final_positions
        final_positions = cartesian_positions[:]  # type: ignore
        if projection_parameters.invert_x_axis:
            final_positions[:, 0] = 1 - normalize_array(final_positions[:, 0])
        if projection_parameters.use_polar_coordinates:
            final_positions = polar_to_cartesian(1 - normalize_array(final_positions[:, 0]), normalize_array(final_positions[:, 1]) * np.pi * 2)
        map_data["results"]["per_point_data"]["positions_x"] = final_positions[:, 0].tolist()
        map_data["results"]["per_point_data"]["positions_y"] = final_positions[:, 1].tolist()
        map_data["results"]["last_position_update"] = time.time()

    if reduced_dimensions_required:
        map_vector_field = params.vectorize.map_vector_field

        cluster_hints = params.projection.get("cluster_hints", "")
        if cluster_hints:
            cluster_hints = [hint.strip() for hint in cluster_hints.split(",")]
            logging.warning(f"cluster hints: {cluster_hints}")
            example_dataset = datasets[sorted_ids[0][0]]
            # generator_function = get_generator_function_from_field(example_dataset.schema.object_fields[map_vector_field])
            # cluster_hint_embeddings = np.asarray(generator_function(cluster_hints))
            # dummy_vector = np.zeros(len(cluster_hints))
            # org_vectors = np.asarray(get_field_from_all_items(items_by_dataset, sorted_ids, map_vector_field, dummy_vector))
            # vectors = np.dot(org_vectors, cluster_hint_embeddings.T)
            # # vectors has 2000 rows and 7 columns, normalize each column separately to 0-1:
            # #vectors = (vectors - vectors.min(axis=0)) / (vectors.max(axis=0) - vectors.min(axis=0))

            vector_size = 256 if map_vector_field == "w2v_vector" else get_vector_field_dimensions(example_dataset.schema.object_fields[map_vector_field])
            # in the case the map vector can't be generated (missing images etc.), use a dummy vector:
            dummy_vector = np.zeros(vector_size)
            vectors = np.asarray(get_field_from_all_items(items_by_dataset, sorted_ids, map_vector_field, dummy_vector))

            for i, ds_and_item_id in enumerate(sorted_ids):
                ds_id, item_id = ds_and_item_id
                item = items_by_dataset[ds_id][item_id]
                title_abstract = item.get("title", "") + " " + item.get("abstract", "")
                vectors[i][:len(cluster_hints)] = [1 if hint.lower() in title_abstract.lower() else 0 for hint in cluster_hints]

        else:
            example_dataset = datasets[sorted_ids[0][0]]
            vector_size = 256 if map_vector_field == "w2v_vector" else get_vector_field_dimensions(example_dataset.schema.object_fields[map_vector_field])
            # in the case the map vector can't be generated (missing images etc.), use a dummy vector:
            dummy_vector = np.zeros(vector_size)
            vectors = np.asarray(get_field_from_all_items(items_by_dataset, sorted_ids, map_vector_field, dummy_vector))
        timings.log("convert to numpy")

        def apply_projections_to_positions(raw_projections):
            nonlocal cartesian_positions, final_positions
            if projection_parameters.x_axis.type == "embedding" and projection_parameters.y_axis.type == "embedding":
                cartesian_positions = raw_projections
            elif projection_parameters.x_axis.type == "embedding":
                cartesian_positions[:, 0] = raw_projections[:, 0]
            else:  # projection_parameters.y_axis.type == "embedding"
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
        if len(vectors) >= 6:
            dim_reducer = projection_parameters.get("dim_reducer", "umap")
            if dim_reducer == "umap":
                import umap  # import it only when needed as it slows down the startup time
                umap_task = umap.UMAP(n_components=reduced_dimensions_required, random_state=99,
                                    min_dist=projection_parameters.get("min_dist", 0.17),
                                    n_epochs=projection_parameters.get("n_epochs", 500),
                                    n_neighbors=projection_parameters.get("n_neighbors", 15),
                                    metric=projection_parameters.get("metric", "euclidean"),
                                )
                try:
                    raw_projections = umap_task.fit_transform(vectors, on_progress_callback=on_umap_progress)  # type: ignore
                except (TypeError, ValueError) as e:
                    # might happend when there are too few points
                    logging.warning(f"UMAP failed: {e}")
                    raw_projections = np.zeros((len(vectors), reduced_dimensions_required))
            elif dim_reducer == "pacmap":
                import pacmap
                reducer = pacmap.PaCMAP(n_components=2, n_neighbors=None, MN_ratio=0.5, FP_ratio=2.0)  # type: ignore
                try:
                    raw_projections = reducer.fit_transform(vectors, init="pca")
                except (TypeError, ValueError) as e:
                    # might happend when there are too few points
                    logging.warning(f"PaCMAP failed: {e}")
                    raw_projections = np.zeros((len(vectors), reduced_dimensions_required))
            elif dim_reducer == "umap_cuml_gpu":
                import cuml
                reducer = cuml.manifold.umap.UMAP(n_components=reduced_dimensions_required, random_state=99,  # type: ignore
                                    min_dist=projection_parameters.get("min_dist", 0.17),
                                    n_epochs=projection_parameters.get("n_epochs", 500),
                                    n_neighbors=projection_parameters.get("n_neighbors", 15),
                                    metric=projection_parameters.get("metric", "euclidean"),)
                map_data['progress']['step_title'] = "UMAP fit_transform"
                try:
                    raw_projections = reducer.fit_transform(vectors)
                except (TypeError, ValueError) as e:
                    # might happend when there are too few points
                    logging.warning(f"UMAP failed: {e}")
                    raw_projections = np.zeros((len(vectors), reduced_dimensions_required))
            else:
                logging.warning(f"Unknown dim reducer: {dim_reducer}")
                raw_projections = np.zeros((len(vectors), reduced_dimensions_required))
        else:
            if reduced_dimensions_required == 1:
                raw_projections = np.linspace(0, 1, len(vectors))
            elif reduced_dimensions_required == 2:
                raw_projections = np.zeros((len(vectors), 2))
                # generate a square grid:
                size = int(np.ceil(np.sqrt(len(vectors))))
                for i in range(size):
                    for j in range(size):
                        idx = i * size + j
                        if idx < len(vectors):
                            raw_projections[idx] = [i / size, 1 - (j / size)]
            else:
                raw_projections = np.zeros((len(vectors), reduced_dimensions_required))
        map_data["results"]["per_point_data"]["raw_projections"] = raw_projections.tolist()  # type: ignore
        apply_projections_to_positions(raw_projections)
        timings.log("Dim. Reduction fit transform")
    else:
        # no dim reduction required:
        raw_projections = cartesian_positions

    transform_coordinate_system_and_write_to_map()
    map_data["progress"]["embeddings_available"] = True
    return raw_projections, final_positions  # type: ignore


def reuse_projection_phase(map_data: dict, similar_map: dict) -> tuple[np.ndarray, np.ndarray]:
    raw_projections = similar_map["results"]["per_point_data"]["raw_projections"]
    map_data["results"]["per_point_data"]["positions_x"] = similar_map["results"]["per_point_data"]["positions_x"]
    map_data["results"]["per_point_data"]["positions_y"] = similar_map["results"]["per_point_data"]["positions_y"]
    map_data["results"]["last_position_update"] = time.time()
    final_positions = np.column_stack([map_data["results"]["per_point_data"]["positions_x"], map_data["results"]["per_point_data"]["positions_y"]])
    map_data["progress"]["embeddings_available"] = True
    return raw_projections, final_positions


def clusterize_and_render_phase(map_data: dict, params: DotDict, datasets: dict, items_by_dataset: dict, sorted_ids: list[tuple[str, str]], raw_projections: np.ndarray, final_positions: np.ndarray, timings: Timings):
    map_data['progress']['step_title'] = "Clusterize results"
    if len(sorted_ids) >= 6:
        cluster_id_per_point: np.ndarray = clusterize_results(raw_projections, params.rendering.clusterizer_parameters)
    else:
        cluster_id_per_point = np.zeros(len(sorted_ids), dtype=int) - 1
    map_data["results"]["per_point_data"]["cluster_ids"] = cluster_id_per_point.tolist()
    timings.log("clustering")

    map_data['progress']['step_title'] = "Find cluster titles"
    if any(datasets[ds_id].schema.descriptive_text_fields for ds_id in datasets.keys()):
        if len(sorted_ids) >= 6:
            result_language = params.search.result_language
            cluster_data = get_cluster_titles(cluster_id_per_point, final_positions, sorted_ids, items_by_dataset, datasets, result_language, timings)
        else:
            cluster_data = {}
        map_data["results"]["clusters"] = cluster_data
    else:
        map_data["results"]["clusters"] = {}

    for attr in ["size", "hue", "val", "sat", "opacity", "secondary_hue", "secondary_val", "secondary_sat", "secondary_opacity", "flatness"]:
        attr_type = params.rendering[attr].type
        attr_parameter = params.rendering[attr].parameter
        if attr_type == "number_field":
            field = attr_parameter
            for ds_id, ds_items in items_by_dataset.items():
                fill_in_details_from_text_storage(datasets[ds_id], ds_items, [field])
            values = get_field_from_all_items(items_by_dataset, sorted_ids, field, 0.0)
            map_data["results"]["per_point_data"][attr] = values
        elif attr_type == "count":
            map_data["results"]["per_point_data"][attr] = [len(v) for v in get_field_from_all_items(items_by_dataset, sorted_ids, attr_parameter, [])]
        elif attr_type == "rank":
            map_data["results"]["per_point_data"][attr] = list(range(len(sorted_ids)))
        elif attr_type == "score":
            values = get_field_from_all_items(items_by_dataset, sorted_ids, "_score", 0.0)
            map_data["results"]["per_point_data"][attr] = values
        elif attr_type == "cluster_idx":
            map_data["results"]["per_point_data"][attr] = cluster_id_per_point.tolist()
        elif attr_type == "classifier":
            attr_parameter = DotDict(attr_parameter)
            embedding_space: dict = get_embedding_space_from_ds_and_field([attr_parameter.target_dataset_id, attr_parameter.target_vector_field])  # type: ignore
            decision_vector_data = get_trained_classifier(attr_parameter.collection_id, attr_parameter.class_name, embedding_space.identifier, include_vector=True)
            # logging.warning(f"decision_vector_data: {decision_vector_data} {attr_parameter.collection_id} {attr_parameter.class_name} {embedding_space.identifier}")
            decision_vector = np.array(decision_vector_data.decision_vector)
            # FIXME: assuming here that the vector is already present (e.g. because its the map vector)
            # in the case the map vector can't be generated (missing images etc.), use a dummy vector:
            dummy_vector = np.zeros(embedding_space.dimensions)
            vectors = np.asarray(get_field_from_all_items(items_by_dataset, sorted_ids, attr_parameter.target_vector_field, dummy_vector))
            if attr_parameter.target_vector_field not in items_by_dataset[sorted_ids[0][0]][sorted_ids[0][1]]:
                logging.warning(f"target_vector_field not in first item")
            #logging.warning(f"vectors: {vectors.shape} {decision_vector.shape} {attr_parameter.target_vector_field}")
            #logging.warning(f"{vectors[0][:4]}")
            # using numpy to get dot product between decision vector and all vectors
            scores = np.dot(vectors, decision_vector)
            # making sure that false items are zero and that the positives start at the middle of the scale
            #logging.warning(f"score values: {max(scores)} {min(scores)}")
            if decision_vector_data.threshold is not None and decision_vector_data.highest_score is not None:
                negatives = scores < decision_vector_data.threshold
                scores -= decision_vector_data.threshold
                scores += decision_vector_data.highest_score - decision_vector_data.threshold
                scores[negatives] = 0
            #logging.warning(f"score values: {max(scores)} {min(scores)}")
            map_data["results"]["per_point_data"][attr] = scores.tolist()


def get_map_selection_statistics(map_id: str, selected_ids: list[tuple[int, str]]) -> dict | None:
    if not selected_ids:
        return None
    if map_id not in local_maps:
        # map is not in cache anymore, try to get it from storage again:
        map_data = get_stored_map_data(map_id)
        if map_data:
            local_maps[map_id] = map_data
    map_data = local_maps.get(map_id)
    if not map_data:
        return None
    if not map_data.get("finished"):
        return None
    timings: Timings = Timings()
    params: DotDict = DotDict(map_data["parameters"])
    datasets = {dataset_id: get_dataset(dataset_id) for dataset_id in params.search.dataset_ids}
    sorted_ids = map_data["results"]["per_point_data"]["item_ids"]
    if not sorted_ids:
        return None
    slimmed_items_per_dataset = map_data['results']['slimmed_items_per_dataset']
    items_by_dataset = get_cached_full_item_data(map_id)
    if not items_by_dataset:
        items_by_dataset = {}
        for ds_id, ds_items in slimmed_items_per_dataset.items():
            dataset = datasets[ds_id]
            _, ds_full_items = get_full_results_from_meta_info(dataset, params.vectorize, ds_items, 'map', timings)
            items_by_dataset[ds_id] = ds_full_items
    final_positions = np.column_stack([map_data["results"]["per_point_data"]["positions_x"], map_data["results"]["per_point_data"]["positions_y"]])
    cluster_id_per_point = [0 if any(ds_id == s[0] and item_id == s[1] for s in selected_ids) else 1 for ds_id, item_id in sorted_ids]
    result_language = params.search.result_language
    cluster_data = get_cluster_titles(cluster_id_per_point, final_positions, sorted_ids, items_by_dataset, datasets, result_language, timings)
    return cluster_data[0] if cluster_data else None


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
