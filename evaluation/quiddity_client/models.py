from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SearchTaskSettings(BaseModel):
    search_type: str = "external_input"
    dataset_id: int
    user_input: str  # the raw (potentially natural language) user input
    query: Optional[str] = None  # the processed query
    result_language: Optional[str] = None
    candidates_per_step: int = 10
    queries_per_step: int = 1
    feedback_loop_steps: int = 0
    auto_set_filters: bool = False  # and algorithm and ranking
    filters: Optional[List[str]] = None
    retrieval_mode: Optional[str] = None
    ranking_settings: Optional[Dict] = None

    auto_approve: bool = False
    auto_disapprove: bool = False
    approve_using_comparison: bool = False
    exit_search_mode: bool = False

    min_selections: int = 1
    max_selections: int = 3
    max_selection_candidates: int = 10

    reference_dataset_id: Optional[int] = None
    reference_item_id: Optional[str] = None
    origin_name: Optional[str] = None

    reference_collection_id: Optional[int] = None


class RunSearchTaskPayload(BaseModel):
    collection_id: int
    class_name: str
    search_task: SearchTaskSettings
    wait_for_ms: int = 0


class SearchOrigin(BaseModel):
    type: str | None = None
    field: Any | None = None
    query: str | None = None
    score: float | None = None
    rank: int | None = None


class RelevantPart(BaseModel):
    origin: str | None = None
    field: str | None = None
    index: Any | None = None
    value: str | None = None


class SearchMetadata(BaseModel):
    _id: str | None = None
    _dataset_id: int | None = None
    _origins: List[SearchOrigin] | None = None
    _relevant_parts: List[RelevantPart] | None = None
    _reciprocal_rank_score: float | None = None
    _score: float | None = None
    thumbnail_path: str | None = None
    folder: Any | None = None
    file_name: str | None = None
    file_type: str | None = None
    is_folder: bool | None = None
    content_time: Any | None = None
    description: str | None = None
    content_date: Any | None = None
    language: str | None = None
    abstract: str | None = None
    title: str | None = None
    type_description: str | None = None


class SearchResult(BaseModel):
    id: int | None = None
    collection: int | None = None
    relevance: int | None = None
    search_source_id: str | None = None
    search_score: float | None = None
    is_positive: bool | None = None
    classes: List[str] | None = None
    field_type: str | None = None
    origins: List[Any] | None = None
    dataset_id: int | None = None
    item_id: str | None = None
    metadata: SearchMetadata | None = None
    value: Any | None = None
    relevant_parts: List[RelevantPart] | None = None
    full_text: Any | None = None
    weight: float | None = None
    column_data: Dict[str, Any] | None = None
