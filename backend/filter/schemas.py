from typing import Optional
from ninja import Schema


class CollectionFilter(Schema):
    uid: Optional[str] = None
    display_name: str
    exclusive_for: Optional[str] = None
    removable: bool = True
    filter_type: str  # "text_query", "collection_item_ids", ...
    value: str | list[int]
    field: Optional[str] = None


class AddFilterPayload(Schema):
    collection_id: int
    filter: CollectionFilter


class FilterIdentifierPayload(Schema):
    collection_id: int
    filter_uid: str
