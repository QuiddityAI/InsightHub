from typing import Optional

from ninja import Schema


class CollectionIdentifier(Schema):
    collection_id: int
    class_name: str
