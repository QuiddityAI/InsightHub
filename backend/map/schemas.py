from typing import Optional
from enum import StrEnum

from ninja import Schema

from data_map_backend.schemas import CollectionIdentifier


class MapParameters(Schema):
    # future parameters:
    # vector field
    # point size, star or islands, column to use for clusters / titles etc.
    # umap and clusterizers params
    pass


class NewMapPayload(Schema):
    collection: CollectionIdentifier
    parameters: MapParameters


class PerPointData(Schema):
    ds_and_item_id: list[tuple[int, str]]
    collection_item_id: list[int]
    x: list[float]
    y: list[float]
    cluster_id: list[int]
    size: list[float]
    hue: list[float]
    sat: list[float]
    val: list[float]
    opacity: list[float]
    flatness: list[float]


class ProjectionData(Schema):
    created_at: str  # isoformat
    parameters: MapParameters
    per_point: PerPointData
    text_data_by_item: dict
    colorize_by_cluster_id: bool


class ClusterDescription(Schema):
    id: int
    center: list[float]
    title: str
    title_html: str
    min_score: float
    max_score: float
    avg_score: float
    important_words: list[tuple[str, float]]


class ThumbnailData(Schema):
    atlas_file: str
    aspect_ratio_per_point: list[float]
    sprite_size: int


class MapData(Schema):
    projections_are_ready: bool
    projections: ProjectionData

    clusters_are_ready: bool
    clusters_by_id: dict[int, ClusterDescription]

    thumbnails_are_ready: bool
    thumbnail_data: ThumbnailData | None
