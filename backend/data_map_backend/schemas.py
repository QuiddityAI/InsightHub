from enum import Enum
from typing import Optional

from ninja import Schema


class CollectionItemSizeMode:
    SINGLE_LINE = 1
    SMALL = 2
    FULL = 3


class ItemRelevance:
    RELEVANT_ACCORDING_TO_USER = 2
    RELEVANT_ACCORDING_TO_AI = 1
    CANDIDATE = 0  # e.g. a search result, will be removed when exiting search mode
    NOT_RELEVANT_ACCORDING_TO_AI = -1
    NOT_RELEVANT_ACCORDING_TO_USER = -2


class CollectionIdentifier(Schema):
    collection_id: int
    class_name: str = "_default"


class CollectionUiSettings(Schema):
    secondary_view: Optional[str] = None  # one of 'more', 'map', 'summary'
    secondary_view_is_full_screen: bool = False
    item_layout: str = "columns"  # one of 'columns', 'grid', 'spreadsheet'
    item_size_mode: int = CollectionItemSizeMode.FULL
    show_visibility_filters: bool = False


class SetUiSettingsPayload(Schema):
    collection_id: int
    ui_settings: CollectionUiSettings
