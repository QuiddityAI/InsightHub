import threading
import time
import json
import logging
import uuid

from django.utils import timezone

from data_map_backend.models import DataCollection, User, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType, CollectionItem
from legacy_backend.logic.search import get_search_results
from .schemas import SearchTaskSettings, SearchType, SearchSource, RetrievalMode


def run_search_task(collection: DataCollection, search_task: SearchTaskSettings):
    collection.current_agent_step = "Running search task..."
    collection.last_search_task = search_task.dict()
    collection.save()
    stack_index = max([s.get('stack_index', 0) for s in collection.search_sources if s['is_active']] or [-1]) + 1

    source = SearchSource(
        id_hash=uuid.uuid4().hex,
        created_at=timezone.now().isoformat(),
        search_type=SearchType.EXTERNAL_INPUT,
        dataset_id=search_task.dataset_id,
        stack_index=stack_index,

        # external_input
        query=search_task.query,
        vector=None,
        filters=search_task.filters or [],
        ranking_settings=search_task.ranking_settings or {},
        retrieval_mode=search_task.retrieval_mode or 'hybrid',
        auto_relax_query=True,
        use_reranking=True,

        # similar_to_item
        reference_item_id=None,
        reference_dataset_id=None,
        origin_name=None,

        # similar_to_collection
        reference_collection_id=None,

        # random_sample: no parameters, always same seed

        result_language=search_task.result_language or 'en',
        page_size=10,
        retrieved=0,
        available=None,
        available_is_exact=True,
        is_active=True,

    )

    collection.search_sources.append(source.dict())
    collection.save()
    add_items_from_active_sources(collection)


def add_items_from_active_sources(collection: DataCollection) -> int:
    new_item_count = 0
    for source in collection.search_sources:
        source = SearchSource(**source)
        if not source.is_active:
            continue
        new_item_count += add_items_from_source(collection, source)
    return new_item_count


def add_items_from_source(collection: DataCollection, source: SearchSource) -> int:
    params = {
        'search': {
            'dataset_ids': [source.dataset_id],
            'task_type': 'quick_search',
            'search_type': source.search_type,
            'retrieval_mode': source.retrieval_mode or 'hybrid',
            'use_separate_queries': False,
            'all_field_query': source.query,
            'auto_relax_query': source.auto_relax_query,
            'use_reranking': source.use_reranking,
            'filters': source.filters or [],
            'result_language': source.result_language or 'en',
            'ranking_settings': source.ranking_settings or {},
            'result_list_items_per_page': source.page_size,
            'result_list_current_page': source.retrieved // source.page_size if source.retrieved else 0,
            'max_sub_items_per_item': 1,
            'return_highlights': False,
            'use_bolding_in_highlights': True,
            # TODO: add support for vector search, similar to item, similar to collection
        }
    }
    results = get_search_results(json.dumps(params), 'list')
    items_by_dataset = results['items_by_dataset']
    new_items = []
    for ds_and_item_id in results['sorted_ids']:
        value = items_by_dataset[ds_and_item_id[0]][ds_and_item_id[1]]
        item = CollectionItem(
            date_added=source.created_at,
            search_source_id=source.id_hash,
            collection=collection,
            relevance=0,
            classes=['_default'],
            field_type=FieldType.IDENTIFIER,
            dataset_id=ds_and_item_id[0],
            item_id=ds_and_item_id[1],
            metadata=value,
            search_score=value['_score'],
        )
        new_items.append(item)
    CollectionItem.objects.bulk_create(new_items)

    source.retrieved += len(results['sorted_ids'])
    source.available = max(results['total_matches'], source.retrieved)
    source.available_is_exact = source.retrieval_mode == RetrievalMode.KEYWORD or len(results['sorted_ids']) == 0

    collection.search_sources = [s for s in collection.search_sources if s['id_hash'] != source.id_hash]
    collection.search_sources.append(source.dict())
    collection.items_last_changed = timezone.now()
    collection.save()
    return len(new_items)
