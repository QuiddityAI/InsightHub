from enum import Enum
from typing import Optional

from ninja import Schema

class CollectionItemSizeMode:
    SINGLE_LINE = 1
    SMALL = 2
    FULL = 3


class CollectionIdentifier(Schema):
    collection_id: int
    class_name: str


class CollectionUiSettings(Schema):
    secondary_view: Optional[str] = None  # one of 'more', 'map', 'summary'
    secondary_view_is_full_screen: bool = False
    use_grid_view: bool = False
    item_size_mode: int = CollectionItemSizeMode.FULL


class SetUiSettingsPayload(Schema):
    collection_id: int
    ui_settings: CollectionUiSettings
