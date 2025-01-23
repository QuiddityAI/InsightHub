import logging
import math
import threading

import numpy as np

from data_map_backend.models import DataCollection, Dataset
from data_map_backend.utils import DotDict
from data_map_backend.views.other_views import (
    get_dataset_cached,
    get_serialized_dataset_cached,
)
from legacy_backend.logic.clusters_and_titles import clusterize_results
from legacy_backend.logic.search import get_items_by_ids
from legacy_backend.utils.collect_timings import Timings
from legacy_backend.utils.helpers import normalize_array, polar_to_cartesian
from map.logic.map_generation_steps import (
    do_umap,
    get_cluster_titles_new,
    get_collection_items,
    get_thumbnails,
    get_vector_field_dimensions,
    save_projections,
)

from ..schemas import MapParameters, ProjectionData


def generate_new_map(collection: DataCollection, parameters: MapParameters) -> ProjectionData | str:
    logging.warning("Generating new map")
    timings: Timings = Timings()

    # get collection items and top dataset:
    top_dataset_id, collection_items, reference_ds_and_item_id = get_collection_items(collection)
    item_count = collection_items.count()
    if not item_count:
        return "No items found"
    timings.log("get_collection_items")
    dataset: Dataset = get_dataset_cached(top_dataset_id)
    dataset_serialized = get_serialized_dataset_cached(top_dataset_id)
    timings.log("get_dataset_cached")

    # get data items:
    map_vector_field = dataset.merged_advanced_options.get("map_vector_field", "w2v_vector")
    point_size_field = dataset.merged_advanced_options.get("size_field", None)
    assert dataset.schema.hover_label_rendering is not None
    hover_required_fields = dataset.schema.hover_label_rendering.get("required_fields", [])
    data_item_ids = [item.item_id for item in collection_items]
    required_fields = (
        [map_vector_field] + hover_required_fields if map_vector_field != "w2v_vector" else hover_required_fields
    )
    if point_size_field:
        required_fields.append(point_size_field)
    data_items: list[dict] = get_items_by_ids(dataset.id, data_item_ids, required_fields)  # type: ignore
    reference_data_item = None
    if reference_ds_and_item_id:
        reference_data_item = get_items_by_ids(reference_ds_and_item_id[0], [reference_ds_and_item_id[1]], required_fields)[0]  # type: ignore
    timings.log("get_items_by_ids")

    if item_count >= 5:
        # get vectors:
        if map_vector_field == "w2v_vector":
            # add_w2v_vectors(ds_items, query, similar_map, origin_map,
            #   dataset.schema.descriptive_text_fields, map_data, vectorize_stage_params_hash, timings)
            return "W2V vectors are not supported in the new map"
        else:
            all_map_vectors_present = all([item.get(map_vector_field) is not None for item in data_items])
            if not all_map_vectors_present:
                logging.warning("Not all items have map vectors")
                # TODO: handle this case
        vector_size = (
            256
            if map_vector_field == "w2v_vector"
            else get_vector_field_dimensions(dataset_serialized.schema.object_fields[map_vector_field])
        )
        # in the case the map vector can't be generated (missing images etc.), use a dummy vector:
        dummy_vector = np.zeros(vector_size)
        vectors = [item.get(map_vector_field, dummy_vector) for item in data_items]
        if reference_data_item:
            reference_vector = reference_data_item.get(map_vector_field, dummy_vector)

        # get projections:
        dimensions = 1 if reference_data_item else 2
        raw_projections = do_umap(np.array(vectors), {}, dimensions)
        timings.log("do umap")

        # convert to polar coordinates if similarity map:
        if reference_data_item:
            similarities = np.array([np.dot(reference_vector, vector) for vector in vectors])
            cartesian_positions = np.zeros([len(data_items), 2])
            cartesian_positions[:, 1] = raw_projections[:, 0]
            cartesian_positions[:, 0] = similarities
            final_positions = polar_to_cartesian(
                1 - normalize_array(cartesian_positions[:, 0]), normalize_array(cartesian_positions[:, 1]) * np.pi * 2
            )
        else:
            final_positions = raw_projections

        # clusterize:
        cluster_id_per_point: np.ndarray = clusterize_results(raw_projections, DotDict())
        timings.log("clusterize_results")
    else:
        # arrange items in a grid if there are not enough for umap:
        columns = math.ceil(math.sqrt(item_count))
        raw_projections = np.array([[1 + (i % columns), 1 + (i // columns)] for i in range(item_count)])
        final_positions = raw_projections
        cluster_id_per_point = np.full(item_count, -1)

    # point size:
    if point_size_field:
        point_sizes = np.array([item.get(point_size_field, 1) for item in data_items])
    else:
        point_sizes = np.ones(len(data_items))

    # save projections to collection:
    projection_data = save_projections(
        collection,
        parameters,
        data_items,
        collection_items,
        dataset,
        map_vector_field,
        final_positions,
        cluster_id_per_point,
        point_sizes,
        is_polar=reference_data_item is not None,
        timings=timings,
    )

    # start thread for cluster titles and thumbnails
    threading.Thread(target=get_cluster_titles_new, args=(collection, dataset_serialized, projection_data)).start()
    threading.Thread(target=get_thumbnails, args=()).start()

    timings.print_to_logger()

    # return projections
    return projection_data
