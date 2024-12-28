from typing import Optional
from ninja import Schema


class CollectionFilter(Schema):
    uid: Optional[str] = None
    display_name: str
    removable: bool = True
    filter_type: str  # "text_query", "collection_item_ids", "metadata_value_gte" ...
    value: str | float | int | list[int]
    field: Optional[str] = None


class AddFilterPayload(Schema):
    collection_id: int
    filter: CollectionFilter


class ReplaceRangeFilterPayload(Schema):
    collection_id: int
    field_name: str
    filter: CollectionFilter


class FilterIdentifierPayload(Schema):
    collection_id: int
    filter_uid: str


class ValueRangeInput(Schema):
    collection_id: int
    field_name: str


class ValueRangeOutput(Schema):
    min: float
    max: float
