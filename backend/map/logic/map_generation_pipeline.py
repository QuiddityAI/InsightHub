import logging
import threading

import numpy as np

from ..schemas import MapParameters, ProjectionData

from data_map_backend.views.other_views import (
    get_dataset_cached,
    get_serialized_dataset_cached,
)
from data_map_backend.models import DataCollection, Dataset
from legacy_backend.logic.search import get_items_by_ids
from legacy_backend.utils.dotdict import DotDict
from legacy_backend.logic.clusters_and_titles import clusterize_results
from legacy_backend.utils.collect_timings import Timings

from map.logic.map_generation_steps import (get_collection_items, get_vector_field_dimensions,
    do_umap, save_projections, get_cluster_titles_new, get_thumbnails)


def generate_new_map(
    collection: DataCollection, parameters: MapParameters
) -> ProjectionData | str:
    logging.warning("Generating new map")
    timings: Timings = Timings()

    # get collection items and top dataset:
    top_dataset_id, collection_items, reference_ds_and_item_id = get_collection_items(
        collection
    )
    if not collection_items.count():
        return "No items found"
    timings.log("get_collection_items")
    dataset: Dataset = get_dataset_cached(top_dataset_id)
    dataset_serialized = get_serialized_dataset_cached(top_dataset_id)
    timings.log("get_dataset_cached")

    # get data items:
    map_vector_field = dataset.merged_advanced_options.get(
        "map_vector_field", "w2v_vector"
    )
    assert dataset.schema.hover_label_rendering is not None
    hover_required_fields = dataset.schema.hover_label_rendering.get(
        "required_fields", []
    )
    data_item_ids = [item.item_id for item in collection_items]
    required_fields = [map_vector_field] + hover_required_fields if map_vector_field != "w2v_vector" else hover_required_fields
    data_items: list[dict] = get_items_by_ids(dataset.id, data_item_ids, required_fields)  # type: ignore
    timings.log("get_items_by_ids")

    # get vectors:
    if map_vector_field == "w2v_vector":
        # add_w2v_vectors(ds_items, query, similar_map, origin_map,
        #   dataset.schema.descriptive_text_fields, map_data, vectorize_stage_params_hash, timings)
        return "W2V vectors are not supported in the new map"
    else:
        all_map_vectors_present = all(
            [item.get(map_vector_field) is not None for item in data_items]
        )
        if not all_map_vectors_present:
            logging.warning("Not all items have map vectors")
            # TODO: handle this case
    vector_size = (
        256
        if map_vector_field == "w2v_vector"
        else get_vector_field_dimensions(
            dataset_serialized.schema.object_fields[map_vector_field]
        )
    )
    # in the case the map vector can't be generated (missing images etc.), use a dummy vector:
    dummy_vector = np.zeros(vector_size)
    vectors = [item.get(map_vector_field, dummy_vector) for item in data_items]

    # get projections:
    raw_projections = do_umap(np.array(vectors), {}, 2)
    timings.log("do umap")
    final_positions = raw_projections  # TODO: re-add polar coordinates

    # clusterize:
    cluster_id_per_point: np.ndarray = clusterize_results(raw_projections, DotDict())
    timings.log("clusterize_results")

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
        timings,
    )

    # start thread for cluster titles and thumbnails
    threading.Thread(target=get_cluster_titles_new, args=(collection, dataset_serialized, projection_data)).start()
    threading.Thread(target=get_thumbnails, args=()).start()

    timings.print_to_logger()

    # return projections
    return projection_data
