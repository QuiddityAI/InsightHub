from collections import defaultdict
import json
import logging
import threading

from data_map_backend.models import CollectionItem, CollectionColumn, ServiceUsage, FieldType, WritingTask
from data_map_backend.chatgpt_client import OPENAI_MODELS, get_chatgpt_response_using_history
from data_map_backend.groq_client import GROQ_MODELS, get_groq_response_using_history
from write.prompts import writing_task_prompt
from data_map_backend.utils import DotDict

from legacy_backend.logic.chat_and_extraction import get_item_question_context as get_item_question_context_native
from legacy_backend.logic.search_common import get_document_details_by_id, get_serialized_dataset_cached


def execute_writing_task_thread(task: WritingTask):
    task.is_processing = True
    task.save()

    def execute_writing_task_safe():
        try:
            _execute_writing_task(task)
        except Exception as e:
            logging.error(e)
            import traceback
            logging.error(traceback.format_exc())
            task.is_processing = False
            task.save()

    try:
        thread = threading.Thread(target=execute_writing_task_safe)
        thread.start()
    except Exception as e:
        logging.error(e)
        task.is_processing = False
        task.save()


def _execute_writing_task(task: WritingTask):
    if '_all_columns' in task.source_fields:
        source_columns = CollectionColumn.objects.filter(collection=task.collection)
    else:
        source_column_identifiers = [name.replace("_column__", "") for name in task.source_fields if name.startswith("_column__")]
        source_columns = CollectionColumn.objects.filter(collection=task.collection, identifier__in=source_column_identifiers)
    contexts = []
    items = task.collection.collectionitem_set.filter(relevance__gte=1) if task.use_all_items else [CollectionItem.objects.get(id=item_id) for item_id in task.selected_item_ids]
    references = []
    for item in items:
        text = None
        if item.field_type == FieldType.TEXT:
            # TODO: use same format as for other items
            text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
        if item.field_type == FieldType.IDENTIFIER:
            assert item.dataset_id is not None
            assert item.item_id is not None
            text = f"Document ID: {len(references) + 1}\n" + get_item_question_context_native(item.dataset_id, item.item_id, task.source_fields, task.prompt)['context']
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

    context = "\n\n".join(contexts)

    full_prompt = writing_task_prompt.replace("{{ context }}", context)
    # logging.warning(full_prompt)
    history = [ { "role": "system", "content": full_prompt }, { "role": "user", "content": task.prompt }]
    cost_per_module = {
        'openai_gpt_3_5': 1.0,
        'openai_gpt_4_turbo': 5.0,
        'openai_gpt_4_o': 2.5,
        'groq_llama_3_8b': 0.2,
        'groq_llama_3_70b': 0.5,
        'python_expression': 0.0,
        'website_scraping': 0.0,
        'notes': 0.0,
    }
    module = task.module or "openai_gpt_3_5"

    usage_tracker = ServiceUsage.get_usage_tracker(task.collection.created_by, "External AI")
    result = usage_tracker.track_usage(cost_per_module.get(module, 1.0), f"execute writing task using {module}")
    if result["approved"]:
        if module.startswith("openai_gpt"):
            openai_model = {
                "openai_gpt_3_5": OPENAI_MODELS.GPT3_5,
                "openai_gpt_4_turbo": OPENAI_MODELS.GPT4_TURBO,
                "openai_gpt_4_o": OPENAI_MODELS.GPT4_O,
            }
            response_text = get_chatgpt_response_using_history(history, openai_model[module])
        elif module.startswith("groq_"):
            groq_models = {
                "groq_llama_3_8b": GROQ_MODELS.LLAMA_3_8B,
                "groq_llama_3_70b": GROQ_MODELS.LLAMA_3_70B,
            }
            response_text = get_groq_response_using_history(history, groq_models[module])
        else:
            response_text = "AI module not found."
    else:
        response_text = "AI usage limit exceeded."
    #response_text = "n/a"
    # logging.warning(response_text)

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

    if not task.previous_versions:
        task.previous_versions = []  # type: ignore
    task.previous_versions.append({
        'created_at': task.changed_at.isoformat(),
        'text': task.text,
        'additional_results': task.additional_results,
    })
    if len(task.previous_versions) > 3:
        task.previous_versions = task.previous_versions[-3:]  # type: ignore
    task.text = response_text
    task.additional_results = {
        'used_prompt': full_prompt,
        'references': references,
        'reference_metadata': metadata,
    }
    task.is_processing = False
    task.save()