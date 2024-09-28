from typing import Optional

from ninja import Schema


class CreateCollectionSettings(Schema):
    related_organization_id: int
    dataset_id: int
    mode: str
    auto_set_filters: bool
    query: Optional[str]
    result_language: Optional[str]
    search_algorithm: Optional[str]
    ranking_settings: Optional[dict]
