from typing import Optional

from ninja import Schema


class SearchTaskSettings(Schema):
    dataset_id: int
    query: str
    result_language: Optional[str] = None
    candidates_per_step: int = 10
    queries_per_step: int = 1
    feedback_loop_steps: int = 0
    auto_set_filters: bool = False  # and algorithm and ranking
    filters: Optional[dict] = None
    retrieval_mode: Optional[str] = None
    ranking_settings: Optional[dict] = None
    auto_select: bool = False
    min_selections: int = 1
    max_selections: int = 3
    max_selection_candidates: int = 10
