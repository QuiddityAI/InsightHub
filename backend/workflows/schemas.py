from typing import Optional

from ninja import Schema


class CreateCollectionSettings(Schema):
    related_organization_id: int
    dataset_id: int
    mode: str
    auto_set_filters: bool
    filters: Optional[list]
    user_input: Optional[str]
    result_language: Optional[str]
    retrieval_mode: Optional[str]
    ranking_settings: Optional[dict]
