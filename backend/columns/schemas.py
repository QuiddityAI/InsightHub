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
