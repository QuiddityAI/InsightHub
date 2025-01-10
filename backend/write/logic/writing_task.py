from collections import defaultdict
import json
import logging
import threading

from llmonkey.llms import BaseLLMModel, Google_Gemini_Flash_1_5_v1

from data_map_backend.models import CollectionItem, CollectionColumn, ServiceUsage, FieldType, WritingTask
from write.prompts import writing_task_prompt
from data_map_backend.utils import DotDict

from legacy_backend.logic.chat_and_extraction import get_item_question_context as get_item_question_context_native
from legacy_backend.logic.search_common import get_document_details_by_id, get_serialized_dataset_cached


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
    if not task.prompt:
        task.is_processing = False
        task.save()
        return
    assert isinstance(task.source_fields, list)
    if '_all_columns' in task.source_fields:
        source_columns = CollectionColumn.objects.filter(collection=task.collection)
    else:
        source_column_identifiers = [name.replace("_column__", "") for name in task.source_fields if name.startswith("_column__")]
        source_columns = CollectionColumn.objects.filter(collection=task.collection, identifier__in=source_column_identifiers)
    contexts = []
    items: list[CollectionItem] = []
    if task.use_all_items:
        items = task.collection.items.filter(relevance__gte=0)  # type: ignore
    else:
        assert isinstance(task.selected_item_ids, list)
        items = [CollectionItem.objects.get(id=item_id) for item_id in task.selected_item_ids]
    references = []
    for item in items:
        text = None
        if item.field_type == FieldType.TEXT:
            # TODO: use same format as for other items
            text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
        elif item.field_type == FieldType.IDENTIFIER:
            assert item.dataset_id is not None
            assert item.item_id is not None
            item_context = get_item_question_context_native(item.dataset_id, item.item_id, task.source_fields, task.prompt)['context']
            text = f"Document ID: {len(references) + 1}\n{item_context}"
            for additional_source_column in source_columns:
                if not item.column_data:
                    continue
                column_data = item.column_data.get(additional_source_column.identifier)
                if column_data and column_data.get('value'):
                    if "\n" in column_data['value']:
                        text += f"{additional_source_column.name}:\n{column_data['value']}\n"
                    else:
                        text += f"{additional_source_column.name}: {column_data['value']}\n"
            references.append((item.dataset_id, item.item_id))
        if not text:
            continue
        contexts.append(text)

    for previous_task in WritingTask.objects.filter(collection=task.collection).order_by('created_at')[:3]:
        if previous_task == task:
            continue
        contexts.append(f"Previously answered question: \"{previous_task.prompt}\":\nGenerated Response:\n{previous_task.text}")

    context = "\n\n".join(contexts)

    system_prompt = writing_task_prompt.replace("{{ context }}", context)
    user_prompt = task.prompt
    # logging.warning(system_prompt)

    default_model = Google_Gemini_Flash_1_5_v1.__name__
    model = BaseLLMModel.load(task.module or default_model)

    # necessary 'AI credits' is defined by us as the cost per 1M tokens / factor:
    ai_credits = model.config.euro_per_1M_output_tokens / 5.0
    usage_tracker = ServiceUsage.get_usage_tracker(task.collection.created_by.id, "External AI")  # type: ignore
    result = usage_tracker.track_usage(ai_credits, f"write summary using {model.__class__.__name__}")
    if result['approved'] == True:
        response = model.generate_prompt_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=None,
        )
        response_text = response.conversation[-1].content
    else:
        response_text = "AI usage limit exceeded"

    assert response_text is not None
    used_references = []
    for i, reference in enumerate(references):
        if f"[{i + 1}]" in response_text:
            used_references.append(reference)
            response_text = response_text.replace(f"[{i + 1}]", f"[{reference[0]}, {reference[1]}]")

    metadata = defaultdict(dict)
    for reference in used_references:
        dataset = DotDict(get_serialized_dataset_cached(reference[0]))
        item = get_document_details_by_id(reference[0], reference[1], tuple(dataset.schema.result_list_rendering.required_fields))
        metadata[reference[0]][reference[1]] = item

    task.previous_versions.append({
        'created_at': task.changed_at.isoformat(),
        'text': task.text,
        'additional_results': task.additional_results,
    })
    if len(task.previous_versions) > 3:
        task.previous_versions = task.previous_versions[-3:]  # type: ignore
    task.text = response_text
    task.additional_results = {  # type: ignore
        'used_prompt': f"system_prompt: {system_prompt}\nuser_prompt: {user_prompt}",
        'references': references,
        'reference_metadata': metadata,
    }
    task.is_processing = False
    task.save()
