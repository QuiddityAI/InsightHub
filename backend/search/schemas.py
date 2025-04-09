from enum import StrEnum
from typing import Optional

from ninja import Schema


class SearchType(StrEnum):
    EXTERNAL_INPUT = "external_input"
    SIMILAR_TO_ITEM = "similar_to_item"
    SIMILAR_TO_COLLECTION = "similar_to_collection"
    RANDOM_SAMPLE = "random_sample"


class RetrievalMode(StrEnum):
    HYBRID = "hybrid"
    KEYWORD = "keyword"
    VECTOR = "vector"


class SearchTaskSettings(Schema):
    search_type: SearchType = SearchType.EXTERNAL_INPUT  # normal (external_input), similarity search or random sample
    dataset_id: int
    user_input: str  # the raw (potentially natural language) user input
    vector: list[float] | None = None  # search query as vector, user_input is ignored if set
    result_language: Optional[str] = None  # might be used to filter the results
    auto_set_filters: bool = False  # auto query optimization, filters, ranking + retrieval_mode
    filters: Optional[list] = None
    retrieval_mode: Optional[str] = None  # hybrid, vector, keyword, can be null to be auto-set
    ranking_settings: Optional[dict] = None  # sorting (e.g. relevance or date)
    auto_relax_query: bool = True  # relax query (e.g. remove parts) if no results were found

    auto_approve: bool = False  # either based on relevance column or add all if no relevance column
    approve_using_comparison: bool = False  # compare the top-n results directly using an LLM
    exit_search_mode: bool = False  # leave search mode after auto-approval

    candidates_per_step: int = 10  # aka initially retrieved items / page size, could be e.g. 2000 when building a map

    forced_selections: int = (
        0  # in initial step / round, e.g. 1 when trying to answer a question, 0 when checking if relevant item exists
    )
    min_selections: int = (
        0  # alternative to forced_selections: retrieve new rounds until this number of items is selected (not implemented yet)
    )
    max_candidates: int = (
        100  # before stop looking for min_selections items, or for auto-approval of new items in the background
    )
    max_selections: Optional[int] = None  # limit when answering question, none when looking for complete set

    # similarity search:
    reference_dataset_id: Optional[int] = None
    reference_item_id: Optional[str] = None
    origin_name: Optional[str] = None  # mostly name of reference item for similarity search
    use_reranking: bool = True  # should be always true except when agent handles it


class RetrievalParameters(Schema):
    # Derived from SearchTaskSettings, but more precise for actual retrieval.
    # It is separate from SearchTaskSettings to be able to see what
    # the user specified and what was auto-set.

    created_at: str  # datetime
    search_type: SearchType = SearchType.EXTERNAL_INPUT
    dataset_id: int

    # external_input aka normal search
    keyword_query: Optional[str] = None
    vector: list[float] | None = None
    filters: Optional[list] = None
    ranking_settings: Optional[dict] = None
    retrieval_mode: str = RetrievalMode.HYBRID
    auto_relax_query: bool = True
    use_reranking: bool = (
        True  # should be always true except when no text query is used or items don't have text (e.g. image search)
    )

    # similar_to_item
    reference_dataset_id: Optional[int] = None
    reference_item_id: Optional[str] = None
    origin_name: Optional[str] = None

    # random_sample: no parameters, always same seed

    result_language: Optional[str] = None
    limit: int = 10  # aka page_size / max result count


class RunSearchTaskPayload(Schema):
    collection_id: int
    class_name: str
    search_task: SearchTaskSettings
    wait_for_ms: int = 0


class RunPreviousSearchTaskPayload(Schema):
    collection_id: int
    class_name: str
    wait_for_ms: int = 0


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


class RunExistingSearchTaskPayload(Schema):
    task_id: str
    wait_for_ms: int = 0


class TestNotificationEmailPayload(Schema):
    collection_id: int
    run_on_current_candidates: bool = False
