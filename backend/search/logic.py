import threading
import time
import json
import logging
import uuid
from typing import Callable, Iterable

from django.utils import timezone
from django.db.models import Q

from data_map_backend.models import DataCollection, User, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType, CollectionItem
from data_map_backend.views.question_views import extract_question_from_collection_class_items
from legacy_backend.logic.search import get_search_results
from .schemas import SearchTaskSettings, SearchType, SearchSource, RetrievalMode


def run_search_task(collection: DataCollection, search_task: SearchTaskSettings, user_id: int,
                    after_columns_were_processed: Callable | None=None,
                    is_new_collection: bool = False):
    if not is_new_collection:
        exit_search_mode(collection, '_default')

    collection.current_agent_step = "Running search task..."
    collection.last_search_task = search_task.dict()
    collection.save()
    stack_index = max([s.get('stack_index', 0) for s in collection.search_sources if s['is_active']] or [-1]) + 1

    if search_task.auto_set_filters:
        collection.log_explanation("Use AI model to generate **suitable query** and determine **best filter and ranking settings** (skipped)", save=False)
        # TODO: implement smart search

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

    def after_columns_were_processed_internal(new_items):
        logging.warning("run_search_task: after_columns_were_processed_internal")
        if search_task.auto_approve:
            logging.warning("auto_approve")
            _auto_approve_items(collection, new_items, search_task)

        if search_task.exit_search_mode:
            logging.warning("exit_search_mode")
            exit_search_mode(collection, '_default')

        if after_columns_were_processed:
            after_columns_were_processed(new_items)

    add_items_from_active_sources(collection, user_id, is_new_collection, after_columns_were_processed_internal)


def _auto_approve_items(collection: DataCollection, new_items: list[CollectionItem], search_task: SearchTaskSettings):
    relevance_columns = [column for column in collection.columns.all() if column.determines_relevance]  # type: ignore
    if not relevance_columns:
        return
    changed_items = []
    fallback_items = []
    relevant_items = []
    for item in new_items:
        for column in relevance_columns:  # should be only one in most cases
            assert isinstance(column, CollectionColumn)
            column_content = item.column_data.get(column.identifier)
            if column_content is None:
                continue
            value = column_content.get('value')
            if isinstance(value, dict):
                is_relevant = value.get('is_relevant')
                if is_relevant:
                    relevant_items.append([item, value.get('relevance_score', 0.5)])
                elif value.get('relevance_score', 0.0) > 0.0:
                    fallback_items.append([item, value.get('relevance_score', 0.5)])
    if not relevant_items:
        if fallback_items:
            # if there are not truly relevant items, but some with a relevance score > 0, we take the best one to have at least one
            # (sometimes even items with a low relevance score can be useful by using their fulltext)
            if min([x[1] for x in fallback_items]) != max([x[1] for x in fallback_items]):
                sorted_items = sorted(fallback_items, key=lambda x: x[1], reverse=True)
            relevant_items = fallback_items[:1]
        else:
            return
    if min([x[1] for x in relevant_items]) != max([x[1] for x in relevant_items]):
        sorted_items = sorted(relevant_items, key=lambda x: x[1], reverse=True)
    else:
        # no relevance scores, don't change the order
        sorted_items = relevant_items
    for item, relevance_score in sorted_items[:search_task.max_selections]:
        item.relevance = 2
        changed_items.append(item)
    CollectionItem.objects.bulk_update(changed_items, ['relevance'])
    collection.log_explanation(f"Evaluated top {len(new_items)} items **one-by-one using an LLM** and approved {len(changed_items)} of them", save=True)


def exit_search_mode(collection: DataCollection, class_name: str):
    all_items = CollectionItem.objects.filter(collection=collection, classes__contains=[class_name])
    candidates = all_items.filter(Q(relevance=0) | Q(relevance=1) | Q(relevance=-1))
    num_candidates = candidates.count()
    candidates.delete()
    collection.items_last_changed = timezone.now()

    for source in collection.search_sources:
        source['is_active'] = False

    if num_candidates:
        collection.log_explanation(f"Removed {num_candidates} **not approved** items", save=False)
    collection.save()


def add_items_from_active_sources(collection: DataCollection, user_id: int, is_new_collection: bool = False, after_columns_were_processed: Callable | None=None) -> int:
    new_items = []
    for source in collection.search_sources:
        source = SearchSource(**source)
        if not source.is_active:
            continue
        new_items.extend(add_items_from_source(collection, source, is_new_collection))

    def in_thread():
        max_evaluated_candidates = 10
        for column in collection.columns.all():  # type: ignore
            assert isinstance(column, CollectionColumn)
            if column.auto_run_for_candidates:
                extract_question_from_collection_class_items(new_items[:max_evaluated_candidates], column, collection, user_id)
        if after_columns_were_processed:
            after_columns_were_processed(new_items)

    threading.Thread(target=in_thread).start()

    return len(new_items)


def add_items_from_source(collection: DataCollection, source: SearchSource, is_new_collection: bool = False) -> Iterable[CollectionItem]:
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
            'return_highlights': True,
            'use_bolding_in_highlights': True,
            # TODO: add support for vector search, similar to item, similar to collection
        }
    }
    results = get_search_results(json.dumps(params), 'list')
    items_by_dataset = results['items_by_dataset']
    new_items = []
    existing_item_ids = []
    if not is_new_collection:
        existing_item_ids = CollectionItem.objects.filter(collection=collection, dataset_id=source.dataset_id, item_id__in=[ds_and_item_id[1] for ds_and_item_id in results['sorted_ids']]).values_list('item_id', flat=True)
    for i, ds_and_item_id in enumerate(results['sorted_ids']):
        if ds_and_item_id[1] in existing_item_ids:
            continue
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
            search_score=1 / (source.retrieved + i + 1),
            relevant_parts=value.get('_relevant_parts', []),
        )
        new_items.append(item)
    CollectionItem.objects.bulk_create(new_items)

    source.retrieved += len(results['sorted_ids'])
    source.available = max(results['total_matches'], source.retrieved)
    source.available_is_exact = source.retrieval_mode == RetrievalMode.KEYWORD or len(results['sorted_ids']) < source.page_size

    collection.search_sources = [s for s in collection.search_sources if s['id_hash'] != source.id_hash]
    collection.search_sources.append(source.dict())
    collection.items_last_changed = timezone.now()
    if source.retrieval_mode == RetrievalMode.KEYWORD:
        collection.log_explanation(f"Added {len(new_items)} search results found by **included keywords**", save=False)
    elif source.retrieval_mode == RetrievalMode.VECTOR:
        collection.log_explanation(f"Added {len(new_items)} search results found by **AI-based semantic similarity** (vector search)", save=False)
    elif source.retrieval_mode == RetrievalMode.HYBRID:
        collection.log_explanation(f"Added {len(new_items)} search results found by a combination of **included keywords** and **AI-based semantic similarity** (vector search)", save=False)
    if source.use_reranking:
        collection.log_explanation("Re-ordered top results using an **AI-based re-ranking model**", save=False)
    collection.save()
    return new_items
