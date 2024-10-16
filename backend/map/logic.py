from collections import defaultdict
import logging
import threading
import time

import numpy as np
from django.db.models.manager import BaseManager
from django.utils.timezone import now

from .schemas import MapParameters, ProjectionData, PerPointData, MapData

from data_map_backend.views.other_views import get_filtered_collection_items, get_dataset_cached, get_serialized_dataset_cached
from data_map_backend.models import DataCollection, FieldType, Dataset
from legacy_backend.logic.search import get_items_by_ids
from legacy_backend.utils.dotdict import DotDict
from legacy_backend.logic.clusters_and_titles import clusterize_results
from legacy_backend.utils.collect_timings import Timings


def generate_new_map(collection: DataCollection, parameters: MapParameters) -> ProjectionData | str:
    logging.warning("Generating new map")
    timings: Timings = Timings()
    # generate projections
    top_dataset_id, collection_items, reference_ds_and_item_id = _get_collection_items(collection)
    if not collection_items.count():
        return "No items found"
    timings.log("get_collection_items")
    dataset: Dataset = get_dataset_cached(top_dataset_id)
    dataset_serialized = get_serialized_dataset_cached(top_dataset_id)
    timings.log("get_dataset_cached")

    map_vector_field = dataset.merged_advanced_options.get('map_vector_field', 'w2v_vector')
    assert dataset.schema.hover_label_rendering is not None
    hover_required_fields = dataset.schema.hover_label_rendering.get('required_fields', [])
    item_ids = [item.item_id for item in collection_items]
    items: list[dict] = get_items_by_ids(dataset.id, item_ids, [map_vector_field] + hover_required_fields)  # type: ignore
    timings.log("get_items_by_ids")
    if map_vector_field == "w2v_vector":
        # add_w2v_vectors(ds_items, query, similar_map, origin_map, dataset.schema.descriptive_text_fields, map_data, vectorize_stage_params_hash, timings)
        return "W2V vectors are not supported in the new map"
    else:
        all_map_vectors_present = all([item.get(map_vector_field) is not None for item in items])
        if not all_map_vectors_present:
            logging.warning("Not all items have map vectors")
            # TODO: handle this case

    vector_size = 256 if map_vector_field == "w2v_vector" else get_vector_field_dimensions(dataset_serialized.schema.object_fields[map_vector_field])
    # in the case the map vector can't be generated (missing images etc.), use a dummy vector:
    dummy_vector = np.zeros(vector_size)
    vectors = [item.get(map_vector_field, dummy_vector) for item in items]
    raw_projections = do_umap(np.array(vectors), {}, 2)
    timings.log("do umap")
    final_positions = raw_projections  # TODO: re-add polar coordinates
    cluster_id_per_point: np.ndarray = clusterize_results(raw_projections, DotDict())
    timings.log("clusterize_results")

    per_point = PerPointData(
        ds_and_item_id=[(top_dataset_id, item['_id']) for item in items],
        collection_item_id=[item.id for item in collection_items],
        x=final_positions[:, 0].tolist(),
        y=final_positions[:, 1].tolist(),
        cluster_id=cluster_id_per_point.tolist(),
        size=np.ones(len(items)).tolist(),
        hue=cluster_id_per_point.tolist(),
        sat=np.ones(len(items)).tolist(),
        val=np.ones(len(items)).tolist(),
        opacity=np.ones(len(items)).tolist(),
        flatness=np.ones(len(items)).tolist(),
    )

    text_data_by_item = defaultdict(dict)
    for item in items:
        if map_vector_field in item:
            item.pop(map_vector_field)
        text_data_by_item[dataset.id][item['_id']] = item  # type: ignore

    projection_data = ProjectionData(
        created_at=now().isoformat(),
        parameters=parameters,
        per_point=per_point,
        text_data_by_item=text_data_by_item,
        colorize_by_cluster_id=True,
    )

    map_data = MapData(
        projections_are_ready=True,
        projections=projection_data,
        clusters_are_ready=False,
        clusters_by_id={},
        thumbnails_are_ready=False,
        thumbnail_data=None,
    )
    collection.map_data = map_data.dict()
    timings.log("set data")
    collection.save()
    timings.log("save data")

    # start thread for cluster titles and thumbnails
    threading.Thread(target=get_cluster_titles, args=()).start()
    threading.Thread(target=get_thumbnails, args=()).start()

    timings.print_to_logger()

    # return projections
    return projection_data


def _get_collection_items(collection: DataCollection) -> tuple[int, BaseManager, tuple | None]:
    items, is_search_mode, reference_ds_and_item_id = get_filtered_collection_items(collection, '_default', field_type=FieldType.IDENTIFIER, is_positive=True)
    item_count_per_ds_id = defaultdict(int)
    for item in items:
        item_count_per_ds_id[item.dataset_id] += 1
    top_dataset_id = sorted(item_count_per_ds_id, key=lambda x: item_count_per_ds_id[x], reverse=True)[0]
    items = items.filter(dataset_id=top_dataset_id)
    return top_dataset_id, items, reference_ds_and_item_id


def get_vector_field_dimensions(field: DotDict):
    return field.generator.embedding_space.dimensions if field.generator else \
        (field.embedding_space.dimensions if field.embedding_space else field.index_parameters.vector_size)


def do_umap(vectors: np.ndarray, projection_parameters: dict, reduced_dimensions_required: int) -> np.ndarray:
    from cuml.manifold.umap import UMAP
    # from umap import UMAP  # import it only when needed as it slows down the startup time
    reducer = UMAP(n_components=reduced_dimensions_required, random_state=99,  # type: ignore
                        min_dist=projection_parameters.get("min_dist", 0.17),
                        n_epochs=projection_parameters.get("n_epochs", 500),
                        n_neighbors=projection_parameters.get("n_neighbors", 15),
                        metric=projection_parameters.get("metric", "euclidean"),)
    try:
        raw_projections = reducer.fit_transform(vectors)
    except (TypeError, ValueError) as e:
        # might happend when there are too few points
        logging.warning(f"UMAP failed: {e}")
        raw_projections = np.zeros((len(vectors), reduced_dimensions_required))
    return raw_projections


def get_cluster_titles():
    time.sleep(5)
    return None


def get_thumbnails():
    time.sleep(5)
    return None