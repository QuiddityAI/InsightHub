import json
import logging
import threading

from django.db.models.manager import BaseManager
from llmonkey.llms import BaseLLMModel, Google_Gemini_Flash_1_5_v1

from data_map_backend.models import (
    CollectionColumn,
    CollectionItem,
    FieldType,
    ServiceUsage,
    WritingTask,
)
from data_map_backend.schemas import ItemRelevance
from legacy_backend.logic.chat_and_extraction import (
    get_item_question_context as get_item_question_context_native,
)
from write.prompts import writing_task_prompt, writing_task_prompt_without_items


def execute_writing_task_thread(task: WritingTask):
    task.is_processing = True
    task.save()

    try:
        thread = threading.Thread(target=execute_writing_task_safe, args=(task,))
        thread.start()
    except Exception as e:
        logging.error(e)
        task.is_processing = False
        task.save()


def execute_writing_task_safe(task: WritingTask):
    try:
        _execute_writing_task(task)
    except Exception as e:
        logging.error(e)
        import traceback

        logging.error(traceback.format_exc())
        task.is_processing = False
        task.save()


def _execute_writing_task(task: WritingTask):
    if not task.expression:
        task.is_processing = False
        task.save()
        return

    # source items:
    items: BaseManager[CollectionItem]
    if task.use_all_items:
        items = task.collection.items.filter(relevance__gte=ItemRelevance.APPROVED_BY_AI)  # type: ignore
    else:
        assert isinstance(task.selected_item_ids, list)
        items = CollectionItem.objects.filter(id__in=task.selected_item_ids)
    # same sorting as in UI to have same order of reference numbers:
    if task.collection.search_mode:
        items = items.order_by("-search_score")
    else:
        items = items.order_by("-date_added", "-search_score")

    if not items:
        return _execute_writing_task_without_items(task)

    # source fields:
    assert isinstance(task.source_fields, list)
    if "_all_columns" in task.source_fields:
        source_columns = CollectionColumn.objects.filter(collection=task.collection)
    else:
        source_column_identifiers = [
            name.replace("_column__", "") for name in task.source_fields if name.startswith("_column__")
        ]
        source_columns = CollectionColumn.objects.filter(
            collection=task.collection, identifier__in=source_column_identifiers
        )

    # collect context:
    contexts = []
    provided_data_items = []
    for item in items:
        item_text = None
        if item.field_type == FieldType.TEXT:
            # TODO: use same format as for other items
            item_text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
        elif item.field_type == FieldType.IDENTIFIER:
            assert item.dataset_id is not None
            assert item.item_id is not None
            item_context = get_item_question_context_native(
                item.dataset_id, item.item_id, task.source_fields, task.expression
            )["context"]
            item_text = f"Document ID: {len(provided_data_items) + 1}\n{item_context}"
            for additional_source_column in source_columns:
                if not item.column_data:
                    continue
                column_data = item.column_data.get(additional_source_column.identifier)
                if column_data and column_data.get("value"):
                    if "\n" in column_data["value"]:
                        item_text += f"{additional_source_column.name}:\n{column_data['value']}\n"
                    else:
                        item_text += f"{additional_source_column.name}: {column_data['value']}\n"
            provided_data_items.append((item.dataset_id, item.item_id))
        if not item_text:
            continue
        contexts.append(item_text)

    if task.include_previous_tasks:
        contexts.extend(_get_previous_tasks_context(task))
    context = "\n\n".join(contexts)

    # prompt:
    language = task.parameters.get("language", "en")
    prompt_template = task.prompt_template or writing_task_prompt[language]

    # get LLM answer:
    response_text, model, system_prompt, user_prompt = _format_prompt_and_get_result(task, context, prompt_template)

    # replace reference numbers with actual document IDs:
    for i, ds_and_item_id in enumerate(provided_data_items):
        if f"[{i + 1}]" in response_text:
            response_text = response_text.replace(f"[{i + 1}]", f"[{ds_and_item_id[0]}, {ds_and_item_id[1]}]")

    _move_last_result_to_previous_versions(task)

    # save results:
    task.text = response_text
    task.additional_results = {  # type: ignore
        "used_prompt": f"model: {model.__class__.__name__}\nsystem_prompt: {system_prompt}\nuser_prompt: {user_prompt}",
        "references": provided_data_items,
    }
    task.is_processing = False
    task.save()


def _execute_writing_task_without_items(task: WritingTask):
    assert task.expression is not None
    contexts = []
    if task.include_previous_tasks:
        contexts.extend(_get_previous_tasks_context(task))
    context = "\n\n".join(contexts)

    # prompt:
    language = task.parameters.get("language", "en")
    prompt_template = task.prompt_template or writing_task_prompt_without_items[language]

    # get LLM answer:
    response_text, model, system_prompt, user_prompt = _format_prompt_and_get_result(task, context, prompt_template)

    _move_last_result_to_previous_versions(task)

    # save results:
    task.text = response_text
    task.additional_results = {  # type: ignore
        "used_prompt": f"model: {model.__class__.__name__}\nsystem_prompt: {system_prompt}\nuser_prompt: {user_prompt}",
        "references": [],
    }
    task.is_processing = False
    task.save()


def _get_previous_tasks_context(task: WritingTask):
    contexts = []
    # previous tasks:
    max_previous_tasks = 5
    for previous_task in (
        WritingTask.objects.filter(collection=task.collection)
        .exclude(id=task.id)  # type: ignore
        .order_by("created_at")
    )[:max_previous_tasks]:
        contexts.append(
            f'Previously answered question: "{previous_task.expression}":\nGenerated Response:\n{previous_task.text}'
        )
    return contexts


def _format_prompt_and_get_result(task: WritingTask, context: str, prompt_template):
    assert task.expression is not None
    system_prompt = prompt_template.replace("{{ context }}", context)
    if "{{ expression }}" in prompt_template:
        system_prompt = system_prompt.replace("{{ expression }}", task.expression)
        user_prompt = ""
    else:
        user_prompt = task.expression

    default_model = Google_Gemini_Flash_1_5_v1.__name__
    model = BaseLLMModel.load(task.model or default_model)

    # necessary 'AI credits' is defined by us as the cost per 1M tokens / factor:
    ai_credits = model.config.euro_per_1M_output_tokens / 5.0
    usage_tracker = ServiceUsage.get_usage_tracker(task.collection.created_by.id, "External AI")  # type: ignore
    result = usage_tracker.track_usage(ai_credits, f"write summary using {model.__class__.__name__}")
    if result["approved"] == True:
        response = model.generate_prompt_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=None,
        )
        response_text = response.conversation[-1].content
    else:
        response_text = "AI usage limit exceeded"
    assert response_text is not None
    return response_text, model, system_prompt, user_prompt


def _move_last_result_to_previous_versions(task: WritingTask):
    task.previous_versions.append(
        {
            "created_at": task.changed_at.isoformat(),
            "text": task.text,
            "additional_results": task.additional_results,
        }
    )
    if len(task.previous_versions) > 3:
        task.previous_versions = task.previous_versions[-3:]  # type: ignore
