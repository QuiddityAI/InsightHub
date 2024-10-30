from concurrent.futures import ThreadPoolExecutor
import json
import logging
import threading
import time
from typing import Iterable

from django.utils import timezone

from data_map_backend.models import CollectionItem, CollectionColumn, ServiceUsage, FieldType
from data_map_backend.data_backend_client import get_item_question_context
from data_map_backend.chatgpt_client import OPENAI_MODELS, get_chatgpt_response_using_history
from data_map_backend.groq_client import GROQ_MODELS, get_groq_response_using_history
from data_map_backend.prompts import table_cell_prompt

from legacy_backend.logic.chat_and_extraction import get_item_question_context as get_item_question_context_native
from legacy_backend.logic.search_common import get_document_details_by_id, get_serialized_dataset_cached

from columns.logic.website_scraping_column import scrape_website_module
from columns.logic.web_search_column import google_search


def remove_column_data_from_collection_items(collection_items: Iterable[CollectionItem], column_identifier: str):
    items_to_save = []
    for item in collection_items:
        if item.column_data and column_identifier in item.column_data:
            del item.column_data[column_identifier]
            items_to_save.append(item)
    if items_to_save:
        CollectionItem.objects.bulk_update(items_to_save, ["column_data"])


def extract_question_from_collection_class_item_query(collection, class_name, column, offset, limit, order_by, collection_item_id, user_id):
    if collection_item_id:
        collection_items = CollectionItem.objects.filter(id=collection_item_id)
    else:
        collection_items = CollectionItem.objects.filter(collection=collection, is_positive=True, classes__contains=[class_name])
        collection_items = collection_items.order_by(order_by)
        collection_items = collection_items[offset:offset+limit] if limit > 0 else collection_items[offset:]

    def in_thread():
        extract_question_from_collection_class_items(collection_items, column, collection, user_id)

    thread = threading.Thread(target=in_thread)
    thread.start()
    # wait till at least columns_with_running_processes is set:
    time.sleep(0.1)


def extract_question_from_collection_class_items(collection_items, column, collection, user_id):
    collection.columns_with_running_processes.append(column.identifier)
    collection.save()
    try:
        included_items = 0
        batch_size = 10
        for i in range(0, len(collection_items), batch_size):
            batch = collection_items[i:i+batch_size]
            _extract_question_from_collection_class_items_batch(batch, column, collection, user_id)
            included_items += len(batch)
            if included_items % 100 == 0:
                logging.warning(f"Extracted {included_items} items for question {column.name}.")

        logging.warning("Done extracting question from collection class items.")
    except Exception as e:
        logging.error(e)
        import traceback
        logging.error(traceback.format_exc())
    finally:
        collection.columns_with_running_processes.remove(column.identifier)
        collection.save()


def _extract_question_from_collection_class_items_batch(collection_items, column, collection, user_id):
    item_source_fields = [name for name in column.source_fields if not name.startswith("_")]
    source_column_identifiers = [name.replace("_column__", "") for name in column.source_fields if name.startswith("_column__")]
    source_columns = CollectionColumn.objects.filter(collection=collection, identifier__in=source_column_identifiers)
    module_definitions = {
        'llm': {"input_type": "natural_language"},
        'python_expression': {"input_type": "json"},
        'website_scraping': {"input_type": "json"},
        'web_search': {"input_type": "json"},
        'notes': {"input_type": None},
    }
    input_type = module_definitions[column.module]["input_type"]
    def extract(item):
        if (item.column_data or {}).get(column.identifier, {}).get('value'):
            # already extracted (only empty fields are extracted again)
            return
        input_data = None
        if item.field_type == FieldType.TEXT:
            input_data = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
        if item.field_type == FieldType.IDENTIFIER:
            assert item.dataset_id is not None
            assert item.item_id is not None
            if input_type == "natural_language":
                input_data = get_item_question_context(item.dataset_id, item.item_id, column.source_fields, column.expression)
                for additional_source_column in source_columns:
                    if not item.column_data:
                        continue
                    column_data = item.column_data.get(additional_source_column.identifier)
                    if column_data and column_data.get('value'):
                        input_data += f"{additional_source_column.name}: {column_data['value']}\n"
            elif input_type == "json":
                input_data = get_document_details_by_id(item.dataset_id, item.item_id, tuple(item_source_fields))
                assert input_data is not None
                for additional_source_column in source_columns:
                    if not item.column_data:
                        continue
                    column_data = item.column_data.get(additional_source_column.identifier)
                    if column_data and column_data.get('value'):
                        input_data["_column__" + additional_source_column.identifier] = column_data['value']
        if not input_data:
            logging.warning(f"Could not extract question for item {item.id}.")
            return
        cost_per_module = {
            'llm': 0.2,
            'python_expression': 0.0,
            'website_scraping': 0.0,
            'web_search': 0.0,
            'notes': 0.0,
        }
        module = column.module
        cost = cost_per_module.get(module, 1.0)

        if cost > 0:
            usage_tracker = ServiceUsage.get_usage_tracker(user_id, "External AI")
            result = usage_tracker.track_usage(cost, f"extract information using {module}")
        else:
            result = {"approved": True}
        if result["approved"]:
            if module == "python_expression":
                cell_data = {
                    "value": "n/a",
                    "changed_at": timezone.now().isoformat(),
                    "is_ai_generated": False,
                    "is_computed": True,
                    "is_manually_edited": False,
                }
            elif module == "website_scraping":
                cell_data = scrape_website_module(input_data, column.source_fields)
            elif module == "web_search":
                cell_data = google_search(input_data, column.source_fields)
            elif module.startswith("openai_gpt"):
                openai_model = {
                    "openai_gpt_3_5": OPENAI_MODELS.GPT3_5,
                    "openai_gpt_4_turbo": OPENAI_MODELS.GPT4_TURBO,
                    "openai_gpt_4_o": OPENAI_MODELS.GPT4_O,
                }
                if column.prompt_template:
                    prompt = column.prompt_template.replace("{{ document }}", input_data).replace("{{ expression }}", column.expression)
                    history = [ { "role": "system", "content": prompt } ]
                else:
                    prompt = table_cell_prompt.replace("{{ document }}", input_data)
                    history = [ { "role": "system", "content": prompt }, { "role": "user", "content": column.expression } ]
                response_text = get_chatgpt_response_using_history(history, openai_model[module])
                if column.determines_relevance and response_text:
                    try:
                        value = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logging.warning(f"Could not parse response from AI: {response_text} {e}")
                        value = response_text
                else:
                    value = response_text
                cell_data = {
                    'value': value,
                    'changed_at': timezone.now().isoformat(),
                    'is_ai_generated': True,
                    'is_manually_edited': False,
                    'used_prompt': prompt,
                }
            elif module.startswith("groq_"):
                groq_models = {
                    "groq_llama_3_8b": GROQ_MODELS.LLAMA_3_8B,
                    "groq_llama_3_70b": GROQ_MODELS.LLAMA_3_70B,
                }
                if column.prompt_template:
                    prompt = column.prompt_template.replace("{{ document }}", input_data).replace("{{ expression }}", column.expression)
                    history = [ { "role": "system", "content": prompt } ]
                else:
                    prompt = table_cell_prompt.replace("{{ document }}", input_data)
                    history = [ { "role": "system", "content": prompt }, { "role": "user", "content": column.expression } ]
                response_text = get_groq_response_using_history(history, groq_models[module])
                if column.determines_relevance and response_text:
                    try:
                        value = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logging.warning(f"Could not parse response from AI: {response_text} {e}")
                        value = response_text
                else:
                    value = response_text
                cell_data = {
                    'value': value,
                    'changed_at': timezone.now().isoformat(),
                    'is_ai_generated': True,
                    'is_manually_edited': False,
                    'used_prompt': prompt,
                    # potential other fields: used_prompt, used_tokens, used_snippets, fact_checked, edited, ...
                }
            else:
                cell_data = {
                    "value": "Module not found",
                    "changed_at": timezone.now().isoformat(),
                    "is_ai_generated": False,
                    "is_computed": True,
                    "is_manually_edited": False,
                }
        else:
            cell_data = {
                "value": "AI usage limit exceeded",
                "changed_at": timezone.now().isoformat(),
                "is_ai_generated": False,
                "is_computed": True,
                "is_manually_edited": False,
            }

        if item.column_data is None:
            item.column_data = {}  # type: ignore
        item.column_data[column.identifier] = cell_data
        item.save()

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(extract, collection_items)