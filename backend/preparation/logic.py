
from django.utils import timezone

from data_map_backend.models import DataCollection, User
from .schemas import CreateCollectionSettings


def create_collection_using_mode(
    user: User, settings: CreateCollectionSettings
) -> DataCollection:
    item = DataCollection()
    item.created_by = user
    item.name = f"Collection {timezone.now()}"
    item.related_organization_id = settings.related_organization_id  # type: ignore
    item.save()
    return item


def prepare_collection(
    collection: DataCollection, settings: CreateCollectionSettings
) -> DataCollection:
    return collection
