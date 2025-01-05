import threading
import json
import logging
import uuid
from typing import Callable, Iterable

from django.utils import timezone
from llmonkey.llms import Google_Gemini_Flash_1_5_v1

from data_map_backend.models import DataCollection, CollectionColumn, FieldType, CollectionItem
from legacy_backend.logic.search import get_search_results
from search.schemas import SearchTaskSettings, SearchType, SearchSource, RetrievalMode
from columns.logic.process_column import process_cells_blocking
from search.prompts import search_query_prompt
from search.logic.approve_items_and_exit_search import auto_approve_items, approve_using_comparison, exit_search_mode
from search.logic.extract_filters import get_filter_prompt, extract_filters


def run_search_task(collection: DataCollection, search_task: SearchTaskSettings, user_id: int,
                    after_columns_were_processed: Callable | None=None,
                    is_new_collection: bool = False):
    if not is_new_collection:
        exit_search_mode(collection, '_default')

    collection.current_agent_step = "Running search task..."
    collection.last_search_task = search_task.dict()
    collection.search_tasks.append(search_task.dict())
    collection.save()
    # FIXME: stack_index doesn't look right, not sure what the goal was
    stack_index = max([s.get('stack_index', 0) for s in collection.search_sources if s['is_active']] or [-1]) + 1

    search_task.query = search_task.user_input

    if search_task.auto_set_filters:
        collection.log_explanation("Use AI model to generate **suitable query**", save=False)
        prompt = search_query_prompt[search_task.result_language or 'en'].replace("{{ user_input }}", search_task.user_input)
        search_task.query = Google_Gemini_Flash_1_5_v1().generate_short_text(prompt) or search_task.query

        # filter_prompt_template = get_filter_prompt(search_task.dataset_id, search_task.result_language or 'en')
        # if filter_prompt_template:
        #     collection.log_explanation("Use AI model to determine **best filters settings**", save=False)
        #     filter_prompt = filter_prompt_template.replace("{{ user_input }}", search_task.user_input)
        #     filters = extract_filters(search_task, filter_prompt)
        #     if filters:
        #         search_task.filters = filters

        # TODO: also get best ranking mode?

    source = SearchSource(
        id_hash=uuid.uuid4().hex,
        created_at=timezone.now().isoformat(),
        stack_index=stack_index,
        retrieved=0,
        available=None,
        available_is_exact=True,
        is_active=True,

        search_type=search_task.search_type,
        dataset_id=search_task.dataset_id,
        result_language=search_task.result_language or 'en',
        page_size=search_task.candidates_per_step,

        # external_input
        query=search_task.query,
        vector=None,
        filters=search_task.filters or [],
        ranking_settings=search_task.ranking_settings or {},
        retrieval_mode=search_task.retrieval_mode or 'hybrid',
        auto_relax_query=True,
        use_reranking=True,

        # similar_to_item
        reference_item_id=search_task.reference_item_id,
        reference_dataset_id=search_task.reference_dataset_id,
        origin_name=search_task.origin_name,

        # similar_to_collection
        reference_collection_id=search_task.reference_collection_id,

        # random_sample: no parameters, always same seed
    )

    collection.search_sources.append(source.dict())
    collection.save()

    def after_columns_were_processed_internal(new_items):
        if search_task.auto_approve:
            auto_approve_items(collection, new_items, search_task.max_selections)

        if search_task.approve_using_comparison:
            collection.log_explanation("Use AI model to **compare search results** and **approve best items**", save=False)
            approve_using_comparison(collection, new_items, search_task.max_selections, search_task)

        if search_task.exit_search_mode:
            exit_search_mode(collection, '_default')

        if after_columns_were_processed:
            after_columns_were_processed(new_items)

    add_items_from_active_sources(collection, user_id, is_new_collection, after_columns_were_processed_internal)


def add_items_from_active_sources(collection: DataCollection, user_id: int, is_new_collection: bool = False, after_columns_were_processed: Callable | None=None) -> int:
    # removing visibility filters because otherwise new items might not be visible
    collection.filters = []
    collection.save()

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
                process_cells_blocking(new_items[:max_evaluated_candidates], column, collection, user_id)
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
            'internal_input_weight': 0.7,
            'use_similarity_thresholds': True,
            'auto_relax_query': source.auto_relax_query,
            'use_reranking': source.use_reranking if source.search_type == SearchType.EXTERNAL_INPUT else False,
            'filters': source.filters or [],
            'result_language': source.result_language or 'en',
            'ranking_settings': source.ranking_settings or {},
            'similar_to_item_id': [source.reference_dataset_id, source.reference_item_id] if source.reference_item_id else None,

            'result_list_items_per_page': source.page_size,
            'result_list_current_page': source.retrieved // source.page_size if source.retrieved else 0,
            'max_sub_items_per_item': 1,
            'return_highlights': True,
            'use_bolding_in_highlights': True,
            # TODO: add support for vector search, similar to collection
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
