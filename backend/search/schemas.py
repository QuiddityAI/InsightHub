from enum import StrEnum
from typing import Optional

from ninja import Schema


class SearchType(StrEnum):
    EXTERNAL_INPUT = "external_input"
    SIMILAR_TO_ITEM = "similar_to_item"
    SIMILAR_TO_COLLECTION = "similar_to_collection"
    RANDOM_SAMPLE = "random_sample"


class SearchTaskSettings(Schema):
    search_type: SearchType = SearchType.EXTERNAL_INPUT
    dataset_id: int
    user_input: str  # the raw (potentially natural language) user input
    query: str | None = None  # the processed query
    result_language: Optional[str] = None
    candidates_per_step: int = 10
    queries_per_step: int = 1
    feedback_loop_steps: int = 0
    auto_set_filters: bool = False  # and algorithm and ranking
    filters: Optional[list] = None
    retrieval_mode: Optional[str] = None
    ranking_settings: Optional[dict] = None

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


class RunSearchTaskPayload(Schema):
    collection_id: int
    class_name: str
    search_task: SearchTaskSettings
    wait_for_ms: int = 0


class RunPreviousSearchTaskPayload(Schema):
    collection_id: int
    class_name: str
    wait_for_ms: int = 0


class RetrievalMode(StrEnum):
    HYBRID = "hybrid"
    KEYWORD = "keyword"
    VECTOR = "vector"


class RetrievalParameters(Schema):
    created_at: str  # datetime
    search_type: SearchType = SearchType.EXTERNAL_INPUT
    dataset_id: int

    # external_input
    query: Optional[str] = None
    vector: Optional[list] = None
    filters: Optional[list] = None
    ranking_settings: Optional[dict] = None
    retrieval_mode: str = RetrievalMode.HYBRID
    auto_relax_query: bool = True
    use_reranking: bool = True

    # similar_to_item
    reference_dataset_id: Optional[int] = None
    reference_item_id: Optional[str] = None
    origin_name: Optional[str] = None

    # similar_to_collection (also origin_name)
    reference_collection_id: Optional[int] = None

    # random_sample: no parameters, always same seed

    result_language: Optional[str] = None
    page_size: int = 10


class RetrievalStatus(Schema):
    retrieved: int = 0
    available: Optional[int] = None
    available_is_exact: bool = True


class Filter(Schema):
    field: str
    dataset_id: int | None = None
    operator: str
    value: str
    label: str | None = None


class ApprovalUsingComparisonReason(Schema):
    item_id: int
    reason: str


class GetPlainResultsPaylaod(Schema):
    dataset_id: int
    access_token: str
    query_body: dict


class UpdateSearchTaskExecutionSettingsPayload(Schema):
    task_id: str
    updates: dict
