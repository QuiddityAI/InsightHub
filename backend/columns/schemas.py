from typing import Optional
from ninja import Schema


class ColumnConfig(Schema):
    collection_id: int
    name: str | None = None
    identifier: str | None = None
    field_type: str
    expression: str | None = None
    source_fields: list = []
    module: str | None = None
    prompt_template: str | None = None
    auto_run_for_approved_items: bool = False
    auto_run_for_candidates: bool = False
    parameters: dict = {}


class UpdateColumnConfig(Schema):
    column_id: int
    name: str | None = None
    expression: str | None = None
    prompt_template: str | None = None
    auto_run_for_approved_items: bool = False
    auto_run_for_candidates: bool = False
    parameters: dict = {}


class CellDataPayload(Schema):
    collection_item_id: int
    column_identifier: str
    cell_data: dict


class ColumnIdentifier(Schema):
    column_id: int


class ColumnCellRange(Schema):
    column_id: int

    class_name: str = '_default'
    offset: int = 0
    limit: int = -1
    order_by: str = '-date_added'

    collection_item_id: Optional[int] = None  # if provided, only the item with this id will be processed


class ProcessColumnPayload(Schema):
    cell_range: ColumnCellRange
    remove_content: bool = False


class CellData(Schema):
    value: str | dict | list | None = None
    collapsed_label: str | None = None
    used_prompt: str | None = None
    changed_at: str
    is_ai_generated: bool = False
    is_computed: bool = False
    is_manually_edited: bool = False


class Criterion(Schema):
    criteria: str
    fulfilled: bool
    reason: str
    supporting_quote: str | None = None
