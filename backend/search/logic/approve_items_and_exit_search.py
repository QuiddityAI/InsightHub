import logging
from typing import Iterable

from django.utils import timezone
from django.db.models import Q
from django.db.models.manager import BaseManager

from llmonkey.llms import Google_Gemini_Flash_1_5_v1

from data_map_backend.models import (
    DataCollection,
    CollectionColumn,
    CollectionItem,
    FieldType,
    COLUMN_META_SOURCE_FIELDS,
)
from search.prompts import approve_using_comparison_prompt
from search.schemas import SearchTaskSettings, ApprovalUsingComparisonReason
from legacy_backend.logic.chat_and_extraction import get_item_question_context
from columns.schemas import Criterion


def auto_approve_items(
    collection: DataCollection,
    new_items: list[CollectionItem] | BaseManager[CollectionItem],
    max_selections: int | None,
):
    fallback_items = []
    relevant_items = []
    relevance_columns = [column for column in collection.columns.all() if column.module == "relevance"]  # type: ignore
    if relevance_columns:
        for item in new_items:
            for column in relevance_columns:  # should be only one in most cases
                assert isinstance(column, CollectionColumn)
                column_content = item.column_data.get(column.identifier)
                if column_content is None:
                    continue
                value = column_content.get("value")
                if isinstance(value, dict):
                    is_relevant = value.get("is_relevant")
                    if is_relevant:
                        relevant_items.append([item, value.get("relevance_score", 0.5)])
                    elif value.get("relevance_score", 0.0) > 0.0:
                        fallback_items.append([item, value.get("relevance_score", 0.5)])
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
                collection.log_explanation(
                    f"Evaluated top {len(new_items)} items **one-by-one using an LLM**, but couldn't find a relevant one",
                    save=True,
                )
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
    CollectionItem.objects.bulk_update(changed_items, ["relevance"])
    if relevance_columns:
        collection.log_explanation(
            f"Evaluated top {len(new_items)} items **one-by-one using an LLM** and approved {len(changed_items)} of them",
            save=True,
        )
    else:
        collection.log_explanation(f"Added {len(changed_items)} to the collection", save=True)


def approve_using_comparison(
    collection: DataCollection,
    new_items: list[CollectionItem] | BaseManager[CollectionItem],
    max_selections: int | None,
    search_task: SearchTaskSettings,
):
    prompt = approve_using_comparison_prompt[search_task.result_language or "en"]
    prompt = prompt.replace("{{ user_input }}", search_task.user_input)
    relevance_columns = [column for column in collection.columns.all() if column.module == "relevance"]  # type: ignore

    documents = ""
    fields = [
        COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
    ]
    for collection_item in new_items:
        if collection_item.field_type != FieldType.IDENTIFIER:
            continue
        assert collection_item.dataset_id is not None
        assert collection_item.item_id is not None
        input_data = get_item_question_context(
            collection_item.dataset_id, collection_item.item_id, fields, search_task.user_input
        )["context"]
        # input_data has newline at the end
        documents += f"document_id {collection_item.id}:\n{input_data}"  # type: ignore
        for column in relevance_columns:  # should be only one in most cases
            assert isinstance(column, CollectionColumn)
            column_content = collection_item.column_data.get(column.identifier)
            if column_content is None:
                continue
            value = column_content.get("value")
            if isinstance(value, dict):
                criteria_review = value.get("criteria_review", [])
                for criterion in criteria_review:
                    criterion = Criterion(**criterion)
                    documents += f"Relevance: {criterion.reason}\n"
                    if criterion.supporting_quote:
                        documents += f"  Quote: {criterion.supporting_quote}\n"
        documents += "\n"

    prompt = prompt.replace("{{ documents }}", documents)

    results, original_response = Google_Gemini_Flash_1_5_v1().generate_structured_array_response(
        ApprovalUsingComparisonReason,
        system_prompt=prompt,
        user_prompt="",
    )  # type: ignore
    results: Iterable[ApprovalUsingComparisonReason] = results

    relevance_column = relevance_columns[0] if relevance_columns else None
    selected_items = set()
    for result in results:
        collection_item = next((item for item in new_items if item.id == result.item_id), None)  # type: ignore
        if collection_item is None:
            continue
        selected_items.add(collection_item)
        collection_item.relevance = 2
        if relevance_column:
            criterion = Criterion(criteria="Comparison of Documents", fulfilled=True, reason=result.reason)
            add_criterion(collection_item, criterion, relevance_column)
        collection_item.save()

    unselected_items = [item for item in new_items if item not in selected_items]
    for collection_item in unselected_items:
        collection_item.relevance = -1
        if relevance_column:
            criterion = Criterion(criteria="Comparison of Documents", fulfilled=False, reason="Not selected")
            add_criterion(collection_item, criterion, relevance_column)
        collection_item.save()

    CollectionItem.objects.bulk_update(new_items, ["relevance"])


def add_criterion(collection_item: CollectionItem, new_criterion: Criterion, relevance_column: CollectionColumn):
    column_content = collection_item.column_data.get(relevance_column.identifier).get("value", {})
    if isinstance(column_content, dict):
        criteria = [Criterion(**c) for c in column_content.get("criteria_review", [])]
        criteria.append(new_criterion)
        relevance_score = len([c.fulfilled for c in criteria if c.fulfilled]) / max(len(criteria), 1)  # type: ignore
        value = {
            "criteria_review": [c.model_dump() for c in criteria],  # type: ignore
            "is_relevant": relevance_score > 0.6,
            "relevance_score": relevance_score,
        }
        column_content["value"] = value
        column_content["changed_at"] = timezone.now().isoformat()
        collection_item.column_data[relevance_column.identifier] = column_content


def exit_search_mode(collection: DataCollection, class_name: str):
    all_items = CollectionItem.objects.filter(collection=collection, classes__contains=[class_name])
    candidates = all_items.filter(Q(relevance=0) | Q(relevance=1) | Q(relevance=-1))
    num_candidates = candidates.count()
    # TODO: delete only those without column data
    candidates.delete()
    collection.items_last_changed = timezone.now()
    collection.search_mode = False

    if num_candidates:
        collection.log_explanation(f"Removed {num_candidates} **not approved** items", save=False)
    collection.save(update_fields=["items_last_changed", "search_mode", "explanation_log"])


def approve_relevant_search_results(collection: DataCollection, class_name: str):
    all_items = CollectionItem.objects.filter(collection=collection, classes__contains=[class_name])
    candidates = all_items.filter(Q(relevance=0) | Q(relevance=1) | Q(relevance=-1))
    auto_approve_items(collection, candidates, max_selections=None)
    exit_search_mode(collection, class_name)
