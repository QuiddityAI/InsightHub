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
    per_point: PerPointData
    text_data_by_item: dict
    colorize_by_cluster_id: bool
    is_polar: bool = False


class ClusterDescription(Schema):
    id: int
    center: list[float]
    title: str
    title_html: str
    min_score: float
    max_score: float
    avg_score: float
    important_words: list[tuple[str, float]] = []


class ThumbnailData(Schema):
    atlas_file: str
    aspect_ratio_per_point: list[float]
    sprite_size: int


class MapData(Schema):
    projections: ProjectionData
    clusters_by_id: dict[int, ClusterDescription]
    thumbnail_data: ThumbnailData | None


class MapMetadata(Schema):
    created_at: str  # isoformat
    parameters: MapParameters
    projections_are_ready: bool
    clusters_are_ready: bool
    thumbnails_are_ready: bool


class ProjectionsEndpointResponse(Schema):
    projections: ProjectionData
    metadata: dict


class RemoveCollectionItemsPayload(Schema):
    collection_id: int
    item_ids: list[int]


class RemoveCollectionItemsResponse(Schema):
    removed_item_ids: list[int]
    updated_count_per_class: list[dict]
