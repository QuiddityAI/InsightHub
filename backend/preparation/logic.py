from enum import StrEnum
import threading
import time

from django.utils import timezone

from data_map_backend.models import DataCollection, User
from .schemas import CreateCollectionSettings


class CollectionCreationModes(StrEnum):
    QUICK_SEARCH = 'quick_search'
    EMPTY_COLLECTION = 'empty_collection'


def create_collection_using_mode(
    user: User, settings: CreateCollectionSettings
) -> DataCollection:
    item = DataCollection()
    item.created_by = user
    item.name = settings.query or f"Collection {timezone.now().isoformat()}"
    item.related_organization_id = settings.related_organization_id  # type: ignore
    item.agent_is_running = settings.mode != CollectionCreationModes.EMPTY_COLLECTION
    item.current_agent_step = "Preparing..."
    item.cancel_agent_flag = False
    item.save()

    def thread_function():
        try:
            item.current_agent_step = "Finding name..."
            item.save()
            time.sleep(3)
        finally:
            item.agent_is_running = False
            item.save()

    if settings.mode != CollectionCreationModes.EMPTY_COLLECTION:
        threading.Thread(target=thread_function).start()

    return item


def prepare_collection(
    collection: DataCollection, settings: CreateCollectionSettings
) -> DataCollection:
    return collection
