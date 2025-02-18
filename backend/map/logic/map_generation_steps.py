import logging
import time
from collections import defaultdict

import numpy as np
from django.db.models.manager import BaseManager
from django.utils.timezone import now

from data_map_backend.models import DataCollection, Dataset, FieldType
from data_map_backend.utils import DotDict
from data_map_backend.views.other_views import (
    get_dataset_cached,
    get_filtered_collection_items,
    get_serialized_dataset_cached,
)
from legacy_backend.logic.clusters_and_titles import get_cluster_titles
from legacy_backend.logic.search import get_items_by_ids
from legacy_backend.utils.collect_timings import Timings
from map.schemas import (
    ClusterDescription,
    MapData,
    MapMetadata,
    MapParameters,
    PerPointData,
    ProjectionData,
)


def get_collection_items(
    collection: DataCollection,
) -> tuple[int, BaseManager, tuple | None]:
    items, reference_ds_and_item_id = get_filtered_collection_items(
        collection, "_default", field_type=FieldType.IDENTIFIER, is_positive=True
    )
    items = items.only("id", "dataset_id", "item_id")
    if not items:
        return -1, items, reference_ds_and_item_id
    item_count_per_ds_id = defaultdict(int)
    for item in items:
        item_count_per_ds_id[item.dataset_id] += 1
    top_dataset_id = sorted(item_count_per_ds_id, key=lambda x: item_count_per_ds_id[x], reverse=True)[0]
    items = items.filter(dataset_id=top_dataset_id)
    return top_dataset_id, items, reference_ds_and_item_id


def get_vector_field_dimensions(field: DotDict):
    return (
        field.generator.embedding_space.dimensions
        if field.generator
        else (field.embedding_space.dimensions if field.embedding_space else field.index_parameters.vector_size)
    )


def do_umap(vectors: np.ndarray, projection_parameters: dict, reduced_dimensions_required: int) -> np.ndarray:
    # import it only when needed as it slows down the startup time
    try:
        from cuml.manifold.umap import UMAP
    except ImportError:
        from umap import UMAP

    reducer = UMAP(
        n_components=reduced_dimensions_required,
        random_state=99,  # type: ignore
        min_dist=projection_parameters.get("min_dist", 0.17),
        n_epochs=projection_parameters.get("n_epochs", 500),
        n_neighbors=projection_parameters.get("n_neighbors", 15),
        metric=projection_parameters.get("metric", "euclidean"),
    )
    try:
        raw_projections = reducer.fit_transform(vectors)
        assert isinstance(raw_projections, np.ndarray)
    except (TypeError, ValueError) as e:
        # might happend when there are too few points
        logging.warning(f"UMAP failed: {e}")
        raw_projections = np.zeros((len(vectors), reduced_dimensions_required))
    return raw_projections


def save_projections(
    collection: DataCollection,
    parameters: MapParameters,
    data_items: list[dict],
    collection_items: BaseManager,
    dataset: Dataset,
    map_vector_field: str,
    final_positions: np.ndarray,
    cluster_id_per_point: np.ndarray,
    point_sizes: np.ndarray,
    is_polar: bool,
    timings: Timings,
):
    metadata = MapMetadata(
        created_at=now().isoformat(),
        parameters=parameters,
        projections_are_ready=True,
        clusters_are_ready=False,
        thumbnails_are_ready=False,
    )
    collection.map_metadata = metadata.dict()

    per_point = PerPointData(
        ds_and_item_id=[(dataset.id, item["_id"]) for item in data_items],  # type: ignore
        collection_item_id=[item.id for item in collection_items],
        x=final_positions[:, 0].tolist(),
        y=final_positions[:, 1].tolist(),
        cluster_id=cluster_id_per_point.tolist(),
        size=point_sizes.tolist(),
        hue=cluster_id_per_point.tolist(),
        sat=np.ones(len(data_items)).tolist(),
        val=np.ones(len(data_items)).tolist(),
        opacity=np.ones(len(data_items)).tolist(),
        flatness=np.ones(len(data_items)).tolist(),
    )

    text_data_by_item = defaultdict(dict)
    for item in data_items:
        if map_vector_field in item:
            item.pop(map_vector_field)
        text_data_by_item[dataset.id][item["_id"]] = item  # type: ignore

    projection_data = ProjectionData(
        per_point=per_point,
        text_data_by_item=text_data_by_item,
        colorize_by_cluster_id=True,
        is_polar=is_polar,
    )

    map_data = MapData(
        projections=projection_data,
        clusters_by_id={},
        thumbnail_data=None,
    )
    collection.map_data = map_data.dict()
    timings.log("set data")
    collection.save(update_fields=["map_metadata", "map_data"])
    timings.log("save data")

    return projection_data


def get_cluster_titles_new(collection: DataCollection, dataset: DotDict, projection_data: ProjectionData):
    timings: Timings = Timings()
    cluster_id_per_point = projection_data.per_point.cluster_id
    final_positions = np.column_stack([projection_data.per_point.x, projection_data.per_point.y])
    sorted_ids = projection_data.per_point.ds_and_item_id
    items_by_dataset = projection_data.text_data_by_item
    datasets = {dataset.id: dataset}  # type: ignore
    item_count_per_language = defaultdict(int)
    for ds_id, ds_items in items_by_dataset.items():
        for item in ds_items.values():
            item_count_per_language[item.get("language", "en")] += 1
    result_language = max(item_count_per_language, key=lambda x: item_count_per_language[x])
    cluster_data = get_cluster_titles(
        cluster_id_per_point, final_positions, sorted_ids, items_by_dataset, datasets, result_language, timings
    )
    metadata = MapMetadata(**collection.map_metadata)
    metadata.clusters_are_ready = True
    collection.map_metadata = metadata.dict()
    map_data = MapData(**collection.map_data)
    clusters_by_id = {}
    for cluster in cluster_data:
        clusters_by_id[cluster["id"]] = ClusterDescription(**cluster)
    map_data.clusters_by_id = clusters_by_id
    collection.map_data = map_data.dict()
    collection.save()
    timings.log("save data")
    timings.print_to_logger()


def get_important_words(collection: DataCollection, item_ids: list[int]):
    # get data:
    top_dataset_id, filtered_collection_items, reference_ds_and_item_id = get_collection_items(collection)
    if top_dataset_id == -1:
        return []
    all_collection_items = collection.items.only("id", "dataset_id", "item_id").filter(dataset_id=top_dataset_id)  # type: ignore
    dataset: Dataset = get_dataset_cached(top_dataset_id)
    dataset_serialized = get_serialized_dataset_cached(top_dataset_id)
    datasets = {dataset_serialized.id: dataset_serialized}  # type: ignore
    data_item_ids = [item.item_id for item in all_collection_items]
    assert dataset.schema.hover_label_rendering is not None
    hover_required_fields = dataset.schema.hover_label_rendering.get("required_fields", [])
    required_fields = hover_required_fields
    data_items: list[dict] = get_items_by_ids(dataset.id, data_item_ids, required_fields)  # type: ignore
    items_by_dataset = {dataset_serialized.id: {item["_id"]: item for item in data_items}}

    # get top language:
    item_count_per_language = defaultdict(int)
    for ds_id, ds_items in items_by_dataset.items():
        for item in ds_items.values():
            item_count_per_language[item.get("language", "en")] += 1
    result_language = max(item_count_per_language, key=lambda x: item_count_per_language[x])

    # get fake cluster ids and positions:
    sorted_ids = [(item.dataset_id, item.item_id) for item in all_collection_items]
    # TODO: this is inefficient:
    cluster_id_per_point = [0 if item.id in item_ids or not item_ids else 1 for item in all_collection_items]
    final_positions = np.zeros((len(sorted_ids), 2))

    # get title + words for fake cluster:
    cluster_data = get_cluster_titles(
        cluster_id_per_point, final_positions, sorted_ids, items_by_dataset, datasets, result_language, Timings()  # type: ignore
    )
    return cluster_data[0]["important_words"] if cluster_data else []


def get_thumbnails():
    time.sleep(5)
    return None
