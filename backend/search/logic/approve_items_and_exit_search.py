import dspy
from django.db.models import Q
from django.db.models.manager import BaseManager
from django.utils import timezone

from columns.schemas import Criterion
from config.utils import get_default_dspy_llm
from data_map_backend.models import (
    COLUMN_META_SOURCE_FIELDS,
    CollectionColumn,
    CollectionItem,
    DataCollection,
    FieldType,
)
from data_map_backend.schemas import ItemRelevance
from legacy_backend.logic.chat_and_extraction import get_item_question_context
from search.schemas import ApprovalUsingComparisonReason, SearchTaskSettings


class DocComparisonSignature(dspy.Signature):
    """
    Compare the following documents and select those that should be used to answer a question.
    It is possible that no document is relevant. It is also possible that multiple or all documents are relevant.
    If a document is relevant but another is more relevant for the same information, select only the more relevant document.
    Select only as many documents as are necessary to answer the question.
    If multiple documents are very similar or identical, select only the newest one (or the first one, if this cannot be determined).
    Only the metadata of each document will be displayed, not the full content.
    If a relevance justification is provided ("Relevance: reason"), trust this justification.
    """

    documents: list[str] = dspy.InputField()
    target_language: str = dspy.InputField(desc="The desired output language for reason")
    selected_documents: dict[str, str] = dspy.OutputField(
        desc="Dictionary having item_id as key and a very short explanation of why the criterion is fulfilled or not (in target_language)"
    )


doc_comparison = dspy.Predict(DocComparisonSignature)


def auto_approve_items(
    collection: DataCollection,
    new_items: list[CollectionItem] | BaseManager[CollectionItem],
    max_selections: int | None,
    forced_selections: int = 0,
    from_ui: bool = False,
):
    fallback_items = []
    relevant_items = []
    relevance_columns = [column for column in collection.columns.all() if column.module == "relevance"]
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
        if fallback_items and forced_selections:
            # if there are not truly relevant items, but some with a relevance score > 0, we take the best one to have at least one
            # (sometimes even items with a low relevance score can be useful by using their fulltext)
            if min([x[1] for x in fallback_items]) != max([x[1] for x in fallback_items]):
                fallback_items = sorted(fallback_items, key=lambda x: x[1], reverse=True)
            relevant_items = fallback_items[:forced_selections]
        elif forced_selections:
            # no relevant items, but we take one anyway in case our relevance model is wrong:
            relevant_items = [[item, 0.5] for item in new_items[:forced_selections]]
        else:
            # no relevant and no fallback items:
            if relevance_columns and from_ui:
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
        item.relevance = ItemRelevance.APPROVED_BY_AI
        changed_items.append(item)
    CollectionItem.objects.bulk_update(changed_items, ["relevance"])
    if relevance_columns and from_ui:
        collection.log_explanation(
            f"Evaluated top {len(new_items)} items **one-by-one using an LLM** and approved {len(changed_items)} of them",
            save=True,
        )
    elif from_ui:
        collection.log_explanation(f"Added {len(changed_items)} to the collection", save=True)


def approve_using_comparison(
    collection: DataCollection,
    new_items: list[CollectionItem] | BaseManager[CollectionItem],
    search_task: SearchTaskSettings,
    max_selections: int | None = None,
    forced_selections: int = 0,
):
    relevance_columns = [column for column in collection.columns.all() if column.module == "relevance"]

    documents = ""
    fields = [
        COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS,
    ]
    max_items_per_comparison = 15
    for collection_item in new_items[:max_items_per_comparison]:
        if collection_item.field_type != FieldType.IDENTIFIER:
            continue
        assert collection_item.dataset_id is not None
        assert collection_item.item_id is not None
        input_data = get_item_question_context(
            collection_item.dataset_id, collection_item.item_id, fields, search_task.user_input
        )["context"]
        # input_data has newline at the end
        documents += f"document_id {collection_item.id}:\n{input_data}"
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
        documents += "\n\n\n"

    model = get_default_dspy_llm("doc_comparison")
    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        sel_docs = doc_comparison(documents=documents, target_language=search_task.result_language).selected_documents
    results = [ApprovalUsingComparisonReason(item_id=k, reason=v) for k, v in sel_docs.items()]

    relevance_column = relevance_columns[0] if relevance_columns else None
    selected_items = set()
    if max_selections is not None:
        results = list(results)[:max_selections]

    if not results and forced_selections:
        # no results, but we take one anyway in case our relevance model is wrong:
        reason = "Forced selection because no relevant ones were found"
        results = [
            ApprovalUsingComparisonReason(item_id=item.id, reason=reason) for item in new_items[:forced_selections]
        ]

    for result in results:
        collection_item = next((item for item in new_items if item.id == result.item_id), None)
        if collection_item is None:
            continue
        selected_items.add(collection_item)
        collection_item.relevance = ItemRelevance.APPROVED_BY_AI
        if relevance_column:
            criterion = Criterion(criteria="Comparison of Documents", fulfilled=True, reason=result.reason)
            add_criterion(collection_item, criterion, relevance_column)
        collection_item.save()

    unselected_items = [item for item in new_items if item not in selected_items]
    for collection_item in unselected_items:
        collection_item.relevance = ItemRelevance.REJECTED_BY_AI
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


def exit_search_mode(collection: DataCollection, class_name: str, from_ui: bool = False) -> list:
    if not collection.search_mode:
        return []
    # delete candidates without data:
    # (candidates aren't visible outside of search mode anyway, but we don't want to keep them in the database)
    all_items = CollectionItem.objects.filter(collection=collection, classes__contains=[class_name])
    candidates = all_items.filter(relevance=ItemRelevance.CANDIDATE)
    candidates_without_data = candidates.filter(Q(column_data=None) | Q(column_data={}))

    deleted_item_ids = []
    if candidates_without_data:
        deleted_item_ids = list(candidates_without_data.values_list("id", flat=True))
        candidates_without_data.delete()
        collection.items_last_changed = timezone.now()

    collection.search_mode = False

    if from_ui:
        collection.log_explanation(f"Removed any **non-approved** items", save=False)
        collection.save(update_fields=["items_last_changed", "search_mode", "explanation_log"])
    else:
        collection.save(update_fields=["items_last_changed", "search_mode"])
    return deleted_item_ids


def approve_relevant_search_results(collection: DataCollection, class_name: str, from_ui: bool = False):
    all_items = CollectionItem.objects.filter(collection=collection, classes__contains=[class_name])
    candidates = all_items.filter(relevance=ItemRelevance.CANDIDATE)
    auto_approve_items(collection, candidates, max_selections=None, forced_selections=0, from_ui=from_ui)
    exit_search_mode(collection, class_name, from_ui)
