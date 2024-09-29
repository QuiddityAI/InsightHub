from enum import StrEnum
import threading
import time
import json
import logging

from django.utils import timezone

from data_map_backend.models import DataCollection, User, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType, CollectionItem
from legacy_backend.logic.search import get_search_results
from .schemas import SearchTaskSettings


def run_search_task(collection: DataCollection, search_task: SearchTaskSettings):
    collection.current_agent_step = "Running search task..."
    collection.save()
    params = {
        'search': {
            'dataset_ids': [search_task.dataset_id],
            'task_type': 'quick_search',
            'search_type': 'external_input',
            'search_algorithm': search_task.search_algorithm or 'hybrid',
            'use_separate_queries': False,
            'all_field_query': search_task.query,
            'auto_relax_query': True,
            'use_reranking': True,
            'filters': search_task.filters or [],
            'result_language': search_task.result_language or 'en',
            'ranking_settings': search_task.ranking_settings or {},
            'result_list_items_per_page': 10,
            'result_list_current_page': 0,
            'max_sub_items_per_item': 1,
            'return_highlights': False,
            'use_bolding_in_highlights': True,
        }
    }
    results = get_search_results(json.dumps(params), 'list')
    items_by_dataset = results['items_by_dataset']
    new_items = []
    for ds_and_item_id in results['sorted_ids']:
        value = items_by_dataset[ds_and_item_id[0]][ds_and_item_id[1]]
        item = CollectionItem(
            collection=collection,
            relevance=0,
            field_type=FieldType.IDENTIFIER,
            dataset_id=ds_and_item_id[0],
            item_id=ds_and_item_id[1],
            metadata=value,
            search_score=value['_score'],
        )
        new_items.append(item)
    CollectionItem.objects.bulk_create(new_items)
    collection.items_last_changed = timezone.now()
    collection.save()
