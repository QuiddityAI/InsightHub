from django.utils import timezone
from django.db.models import Q
from django.db.models.manager import BaseManager

from data_map_backend.models import DataCollection, CollectionColumn, CollectionItem


def auto_approve_items(collection: DataCollection, new_items: list[CollectionItem] | BaseManager[CollectionItem],
                        max_selections: int | None):
    fallback_items = []
    relevant_items = []
    relevance_columns = [column for column in collection.columns.all() if column.module == 'relevance']  # type: ignore
    if relevance_columns:
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
    else:
        # no relevance column, we just consider all items:
        relevant_items = [[item, 0.5] for item in new_items]

    if not relevant_items:
        if fallback_items:
            # if there are not truly relevant items, but some with a relevance score > 0, we take the best one to have at least one
            # (sometimes even items with a low relevance score can be useful by using their fulltext)
            if min([x[1] for x in fallback_items]) != max([x[1] for x in fallback_items]):
                fallback_items = sorted(fallback_items, key=lambda x: x[1], reverse=True)
            relevant_items = fallback_items[:1]
        else:
            # no relevant and no fallback items:
            if relevance_columns:
                collection.log_explanation(f"Evaluated top {len(new_items)} items **one-by-one using an LLM**, but couldn't find a relevant one", save=True)
            return

    if min([x[1] for x in relevant_items]) != max([x[1] for x in relevant_items]):
        sorted_items = sorted(relevant_items, key=lambda x: x[1], reverse=True)
    else:
        # no relevance scores, don't change the order
        sorted_items = relevant_items

    if max_selections is not None:
        sorted_items = sorted_items[:max_selections]

    changed_items = []
    for item, relevance_score in sorted_items:
        item.relevance = 2
        changed_items.append(item)
    CollectionItem.objects.bulk_update(changed_items, ['relevance'])
    if relevance_columns:
        collection.log_explanation(f"Evaluated top {len(new_items)} items **one-by-one using an LLM** and approved {len(changed_items)} of them", save=True)
    else:
        collection.log_explanation(f"Added {len(changed_items)} to the collection", save=True)


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


def approve_relevant_search_results(collection: DataCollection, class_name: str):
    all_items = CollectionItem.objects.filter(collection=collection, classes__contains=[class_name])
    candidates = all_items.filter(Q(relevance=0) | Q(relevance=1) | Q(relevance=-1))
    auto_approve_items(collection, candidates, max_selections=None)
    exit_search_mode(collection, class_name)