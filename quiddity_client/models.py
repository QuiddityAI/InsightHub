from pydantic import BaseModel
from typing import Any, Optional, List, Dict


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
    type: str
    field: Optional[Any] = None
    query: Optional[str] = None
    score: float
    rank: int


class RelevantPart(BaseModel):
    origin: str
    field: str
    index: Optional[Any] = None
    value: str


class SearchMetadata(BaseModel):
    _id: str
    _dataset_id: int
    _origins: List[SearchOrigin]
    _relevant_parts: List[RelevantPart]
    _reciprocal_rank_score: float
    _score: float
    thumbnail_path: str
    folder: Optional[Any] = None
    file_name: str
    file_type: str
    is_folder: bool
    content_time: Optional[Any] = None
    description: str
    content_date: Optional[Any] = None
    language: str
    abstract: str
    title: str
    type_description: str


class SearchResult(BaseModel):
    id: int
    collection: int
    relevance: int
    search_source_id: str
    search_score: float
    is_positive: bool
    classes: List[str]
    field_type: str
    origins: List[Any]
    dataset_id: int
    item_id: str
    metadata: SearchMetadata
    value: Optional[Any] = None
    relevant_parts: List[RelevantPart]
    full_text: Optional[Any] = None
    weight: float
    column_data: Dict[str, Any]
