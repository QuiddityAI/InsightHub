from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import logging
import threading
import time

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from diskcache import Cache

from ..models import CollectionItem, DataCollection, CollectionColumn, Chat, Dataset, ServiceUsage, FieldType, WritingTask, User
from ..serializers import ChatSerializer, CollectionColumnSerializer, CollectionSerializer, WritingTaskSerializer
from ..data_backend_client import get_item_by_id, get_item_question_context
from ..chatgpt_client import OPENAI_MODELS, get_chatgpt_response_using_history
from ..groq_client import GROQ_MODELS, get_groq_response_using_history
from ..prompts import table_cell_prompt, writing_task_prompt, search_question_prompt, item_relevancy_prompt
from .. import prompts
from ..notifier import default_notifier

from .other_views import is_from_backend


@csrf_exempt
def create_chat_from_search_settings(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        search_settings: dict = data["search_settings"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    chat = Chat.objects.create(
        created_by=request.user,
        search_settings=search_settings,
        name=search_settings['all_field_query'],
    )

    chat.add_question(search_settings['all_field_query'], request.user.id)

    data = ChatSerializer(chat).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


@csrf_exempt
def add_collection_class_chat(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        chat_name: str = data["chat_name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    chat = Chat.objects.create(
        created_by=request.user,
        collection=item,
        class_name=class_name,
        name=chat_name,
    )

    data = ChatSerializer(chat).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


@csrf_exempt
def add_chat_question(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        chat_id: int = data["chat_id"]
        question: str = data["question"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    user = User.objects.get(id=request.user.id)
    username = user.username
    default_notifier.info(f"User {username} asked a question {question}", user=user)

    try:
        item = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    item.add_question(question, request.user.id)
    data = ChatSerializer(item).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


@csrf_exempt
def get_chats(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    chats = Chat.objects.filter(created_by=request.user.id, collection__isnull=True)
    chats = chats.order_by('-created_at')
    chat_ids = [{'id': chat.id, 'name': chat.name} for chat in chats]  # type: ignore

    return HttpResponse(json.dumps(chat_ids), content_type="application/json", status=200)


@csrf_exempt
def get_collection_class_chats(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    chats = Chat.objects.filter(created_by=request.user.id, collection_id=collection_id, class_name=class_name)
    chats = chats.order_by('-created_at')
    chat_ids = [{'id': chat.id, 'name': chat.name} for chat in chats]  # type: ignore

    return HttpResponse(json.dumps(chat_ids), content_type="application/json", status=200)


@csrf_exempt
def get_chat_by_id(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        chat_id: int = data["chat_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    data = ChatSerializer(item).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@csrf_exempt
def delete_chat(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)
    try:
        data = json.loads(request.body)
        chat_id: int = data["chat_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    item.delete()
    return HttpResponse(None, status=204)


@csrf_exempt
def add_collection_column(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        name: str = data["name"]
        identifier: str | None = data.get("identifier", None)
        field_type: str = data["field_type"]
        expression: str | None = data.get("expression")
        source_fields: list = data.get("source_fields", [])
        module: str | None = data.get("module")
        parameters: dict = data.get("parameters", {})
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    if not name.strip():
        return HttpResponse(status=400)

    if not identifier:
        identifier = name.replace(" ", "_").lower()
        tries = 0
        while CollectionColumn.objects.filter(collection_id=collection_id, identifier=identifier).exists():
            identifier += "_"
            tries += 1
            if tries > 10:
                logging.error("Could not create unique identifier for collection column.")
                return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    column = CollectionColumn.objects.create(
        collection_id=collection_id,
        name=name,
        identifier=identifier,
        field_type=field_type,
        expression=expression,
        source_fields=source_fields,
        module=module,
        parameters=parameters,
    )

    data = CollectionColumnSerializer(column).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@csrf_exempt
def delete_collection_column(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        column_id: int = data["column_id"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        column = CollectionColumn.objects.get(id=column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    for item in CollectionItem.objects.filter(collection=column.collection):
        if item.column_data and column.identifier in item.column_data:
            del item.column_data[column.identifier]
            item.save()

    column.delete()

    return HttpResponse(None, status=204)


@csrf_exempt
def set_collection_cell_data(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        item_id: int = data["item_id"]
        column_identifier: int = data["column_identifier"]
        cell_data = data["cell_data"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = CollectionItem.objects.get(id=item_id)
    except CollectionItem.DoesNotExist:
        return HttpResponse(status=404)
    if item.collection.created_by != request.user:
        return HttpResponse(status=401)

    if not item.column_data:
        item.column_data = {}  # type: ignore

    item.column_data[column_identifier] = cell_data
    item.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def extract_question_from_collection_class_items(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        column_id: str = data["column_id"]
        class_name: str = data["class_name"]
        offset: int = data.get("offset", 0)
        limit: int = data.get("limit", -1)
        order_by = data.get("order_by", '-date_added')
        collection_item_id = data.get("collection_item_id")
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        column = CollectionColumn.objects.get(id=column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    if not column.module or column.module == "notes":
        pass
    else:
        _extract_question_from_collection_class_items_thread(column.collection, class_name, column, offset, limit, order_by, collection_item_id, request.user.id)

    data = CollectionSerializer(column.collection).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


def _extract_question_from_collection_class_items_thread(collection, class_name, column, offset, limit, order_by, collection_item_id, user_id):
    collection.columns_with_running_processes.append(column.identifier)
    collection.save()
    def _run_safe():
        try:
            _extract_question_from_collection_class_items(collection, class_name, column, offset, limit, order_by, collection_item_id, user_id)
        except Exception as e:
            logging.error(e)
            import traceback
            logging.error(traceback.format_exc())
        finally:
            collection.columns_with_running_processes.remove(column.identifier)
            collection.save()

    try:
        thread = threading.Thread(target=_run_safe)
        thread.start()
    except Exception as e:
        logging.error(e)
        collection.columns_with_running_processes.remove(column.identifier)
        collection.save()


def _extract_question_from_collection_class_items(collection, class_name, column, offset, limit, order_by, collection_item_id, user_id):
    if collection_item_id:
        collection_items = CollectionItem.objects.filter(id=collection_item_id)
    else:
        collection_items = CollectionItem.objects.filter(collection=collection, is_positive=True, classes__contains=[class_name])
        collection_items = collection_items.order_by(order_by)
        collection_items = collection_items[offset:offset+limit] if limit > 0 else collection_items[offset:]
    included_items = 0
    batch_size = 10
    for i in range(0, len(collection_items), batch_size):
        batch = collection_items[i:i+batch_size]
        _extract_question_from_collection_class_items_batch(batch, column, collection, user_id)
        included_items += len(batch)
        if included_items % 100 == 0:
            logging.warning(f"Extracted {included_items} items for question {column.name}.")

    logging.warning("Done extracting question from collection class items.")


def _extract_question_from_collection_class_items_batch(collection_items, column, collection, user_id):
    item_source_fields = [name for name in column.source_fields if not name.startswith("_")]
    source_column_identifiers = [name.replace("_column__", "") for name in column.source_fields if name.startswith("_column__")]
    source_columns = CollectionColumn.objects.filter(collection=collection, identifier__in=source_column_identifiers)
    module_definitions = {
        'openai_gpt_3_5': {"input_type": "natural_language"},
        'openai_gpt_4_turbo': {"input_type": "natural_language"},
        'openai_gpt_4_o': {"input_type": "natural_language"},
        'groq_llama_3_8b': {"input_type": "natural_language"},
        'groq_llama_3_70b': {"input_type": "natural_language"},
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
                input_data = get_item_by_id(item.dataset_id, item.item_id, item_source_fields)
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
            'openai_gpt_3_5': 1.0,
            'openai_gpt_4_turbo': 5.0,
            'openai_gpt_4_o': 2.5,
            'groq_llama_3_8b': 0.2,
            'groq_llama_3_70b': 0.5,
            'python_expression': 0.0,
            'website_scraping': 0.0,
            'web_search': 0.0,
            'notes': 0.0,
        }
        module = column.module or "openai_gpt_3_5"
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
                cell_data = _scrape_website_module(input_data, column.source_fields)
            elif module == "web_search":
                cell_data = _google_search(input_data, column.source_fields)
            elif module.startswith("openai_gpt"):
                openai_model = {
                    "openai_gpt_3_5": OPENAI_MODELS.GPT3_5,
                    "openai_gpt_4_turbo": OPENAI_MODELS.GPT4_TURBO,
                    "openai_gpt_4_o": OPENAI_MODELS.GPT4_O,
                }
                prompt = table_cell_prompt.replace("{{ document }}", input_data)
                # logging.warning(prompt)
                history = [ { "role": "system", "content": prompt }, { "role": "user", "content": column.expression } ]
                response_text = get_chatgpt_response_using_history(history, openai_model[module])
                cell_data = {
                    'value': response_text,
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
                prompt = table_cell_prompt.replace("{{ document }}", input_data)
                # logging.warning(prompt)
                history = [ { "role": "system", "content": prompt }, { "role": "user", "content": column.expression } ]
                response_text = get_groq_response_using_history(history, groq_models[module])
                cell_data = {
                    'value': response_text,
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


def _scrape_website_module(item, source_fields):
    import requests
    url = item.get(source_fields[0], "")
    if not url:
        return {
            "value": "No URL found",
            "changed_at": timezone.now().isoformat(),
            "is_ai_generated": False,
            "is_computed": True,
            "is_manually_edited": False,
        }
    headers = {'headers':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}
    result = requests.get(url, headers=headers)
    html = result.text
    # rudimentary extraction of text from HTML
    text = ""
    in_tag = False
    for c in html:
        if c == "<":
            in_tag = True
        if not in_tag:
            text += c
        if c == ">":
            in_tag = False
    return {
        "collapsed_label": f"<i>Website Content<br>({len(text.split())} words)</i>",
        "value": text,
        "changed_at": timezone.now().isoformat(),
        "is_ai_generated": False,
        "is_computed": True,
        "is_manually_edited": False,
    }


def _google_search(input_data, source_fields):
    from bs4 import BeautifulSoup
    import requests

    search = input_data.get(source_fields[0], "")
    if not search:
        return {
            "value": "No search query found",
            "changed_at": timezone.now().isoformat(),
            "is_ai_generated": False,
            "is_computed": True,
            "is_manually_edited": False,
        }

    url = 'https://www.google.de/search'

    headers = {
        'Accept' : '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82',
    }
    parameters = {'q': search}

    content = requests.get(url, headers = headers, params = parameters).text
    soup = BeautifulSoup(content, 'html.parser')

    search = soup.find(id = 'search')
    first_link = search.find('a') if search else {}

    url = first_link.get('href') if first_link else ""  # type: ignore

    if not url:
        return {
            "value": "No URL found",
            "changed_at": timezone.now().isoformat(),
            "is_ai_generated": False,
            "is_computed": True,
            "is_manually_edited": False,
        }

    return _scrape_website_module({"url": url}, ["url"])


@csrf_exempt
def remove_collection_class_column_data(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        column_id: str = data["column_id"]
        class_name: str = data["class_name"]
        offset: int = data.get("offset", 0)
        limit: int = data.get("limit", -1)
        order_by = data.get("order_by", '-date_added')
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        column = CollectionColumn.objects.get(id=column_id)
    except CollectionColumn.DoesNotExist:
        return HttpResponse(status=404)
    if column.collection.created_by != request.user:
        return HttpResponse(status=401)

    collection_items = CollectionItem.objects.filter(collection=column.collection, classes__contains=[class_name])
    collection_items = collection_items.order_by(order_by)
    collection_items = collection_items[offset:offset+limit] if limit > 0 else collection_items[offset:]
    for item in collection_items:
        if item.column_data and column.identifier in item.column_data:
            del item.column_data[column.identifier]
            item.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def track_service_usage(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        service_name: str = data["service_name"]
        amount: int = data["amount"]
        cause: str = data["cause"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    usage_tracker = ServiceUsage.get_usage_tracker(user_id, service_name)
    result = usage_tracker.track_usage(amount, cause)

    return HttpResponse(json.dumps(result), content_type="application/json", status=200)


@csrf_exempt
def get_service_usage(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)
    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        service_name: str = data["service_name"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    usage_tracker = ServiceUsage.get_usage_tracker(user_id, service_name)
    result = {
        'usage_current_period': usage_tracker.get_current_period().usage,
        'limit_per_period': usage_tracker.limit_per_period,
        'period_type': usage_tracker.period_type,
    }

    return HttpResponse(json.dumps(result), content_type="application/json", status=200)


@csrf_exempt
def get_writing_tasks(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data['collection_id']
        class_name: str = data['class_name']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    tasks = WritingTask.objects.filter(collection_id=collection_id, class_name=class_name)
    tasks = tasks.order_by('-created_at')

    task_ids = [{'id': task.id, 'name': task.name} for task in tasks]  # type: ignore

    return HttpResponse(json.dumps(task_ids), content_type="application/json", status=200)


@csrf_exempt
def add_writing_task(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data['collection_id']
        class_name: str = data['class_name']
        name: str = data['name']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    task = WritingTask.objects.create(
        collection_id=collection_id,
        class_name=class_name,
        name=name,
        module='openai_gpt_4_o',
    )

    data = WritingTaskSerializer(task).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


@csrf_exempt
def get_writing_task_by_id(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    data = WritingTaskSerializer(task).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


@csrf_exempt
def delete_writing_task(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    task.delete()
    return HttpResponse(None, status=204)


@csrf_exempt
def update_writing_task(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
        name: str = data['name']
        source_fields: list = data.get('source_fields', [])
        use_all_items: bool = data.get('use_all_items', True)
        selected_item_ids: list = data.get('selected_item_ids', [])
        module: str | None = data.get('module', None)
        parameters: dict = data.get('parameters', {})
        prompt: str | None = data.get('prompt', None)
        text: str | None = data.get('text', None)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    task.name = name
    task.source_fields = source_fields  # type: ignore
    task.use_all_items = use_all_items
    task.selected_item_ids = selected_item_ids  # type: ignore
    task.module = module
    task.parameters = parameters  # type: ignore
    if prompt is not None:
        task.prompt = prompt
    if text is not None and text != task.text:
        if not task.previous_versions:
            task.previous_versions = []  # type: ignore
        task.previous_versions.append({
            'created_at': task.changed_at.isoformat(),
            'text': task.text,
            'additional_results': task.additional_results,
        })
        if len(task.previous_versions) > 3:
            task.previous_versions = task.previous_versions[-3:]  # type: ignore
        task.text = text
    task.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def revert_writing_task(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    if not task.previous_versions:
        return HttpResponse(status=400)

    last_version = task.previous_versions.pop()
    task.text = last_version['text']
    task.additional_results = last_version['additional_results']
    task.save()

    return HttpResponse(None, status=204)


@csrf_exempt
def execute_writing_task(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        task_id: int = data['task_id']
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        task = WritingTask.objects.get(id=task_id)
    except WritingTask.DoesNotExist:
        return HttpResponse(status=404)
    if task.collection.created_by != request.user:  # type: ignore
        return HttpResponse(status=401)

    _execute_writing_task_thread(task)

    return HttpResponse(None, status=204)


def _execute_writing_task_thread(task):
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


def _execute_writing_task(task):
    source_column_identifiers = [name.replace("_column__", "") for name in task.source_fields if name.startswith("_column__")]
    source_columns = CollectionColumn.objects.filter(collection=task.collection, identifier__in=source_column_identifiers)
    contexts = []
    items = task.collection.collectionitem_set.all() if task.use_all_items else [CollectionItem.objects.get(id=item_id) for item_id in task.selected_item_ids]
    references = []
    for item in items:
        text = None
        if item.field_type == FieldType.TEXT:
            # TODO: use same format as for other items
            text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
        if item.field_type == FieldType.IDENTIFIER:
            assert item.dataset_id is not None
            assert item.item_id is not None
            text = f"Document ID: {len(references) + 1}\n" + get_item_question_context(item.dataset_id, item.item_id, task.source_fields, task.prompt)
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
    # logging.warning(prompt)
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
    }
    task.is_processing = False
    task.save()


@csrf_exempt
def answer_question_using_items(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        question: str = data["question"]
        ds_and_item_ids: list = data["ds_and_item_ids"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    source_fields = ["_descriptive_text_fields", "_full_text_snippets"]

    texts = []
    for ds_id, item_id in ds_and_item_ids:
        text = f"Document ID: [{ds_id}, {item_id}]\n" + get_item_question_context(ds_id, item_id, source_fields, question)
        texts.append(text)

    context = "\n\n".join(texts)

    prompt = search_question_prompt.replace("{{ context }}", context).replace("{{ question }}", question)

    history = [ { "role": "system", "content": prompt } ]

    response_text = get_chatgpt_response_using_history(history, OPENAI_MODELS.GPT4_O)

    return HttpResponse(json.dumps({"answer": response_text, "prompt": prompt}), content_type="application/json", status=200)


@csrf_exempt
def judge_item_relevancy_using_llm(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        user_id: int = data["user_id"]
        question: str = data["question"]
        dataset_id: int = data["dataset_id"]
        item_id: str = data["item_id"]
        delay: int = data.get("delay", 0)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    relevancy = _judge_item_relevancy_using_llm(user_id, question, dataset_id, item_id, delay)

    return HttpResponse(json.dumps(relevancy), content_type="application/json", status=200)


item_relevancy_cache = None


def _judge_item_relevancy_using_llm(user_id: int, question: str, dataset_id: int, item_id: str,
                                    delay: int = 0) -> dict:
    global item_relevancy_cache
    if not item_relevancy_cache:
        # create it here and note above, as otherwise it would also be created when management commands are run
        # and in this case it might not be from the docker container and the /data/ folder might not be available
        item_relevancy_cache = Cache("/data/quiddity_data/item_relevancy_cache/")
    cache_key = f"{question}_{dataset_id}_{item_id}"
    if cache_key in item_relevancy_cache:
        return item_relevancy_cache.get(cache_key)  # type: ignore

    source_fields = ["_descriptive_text_fields", "_full_text_snippets"]
    item_context = get_item_question_context(dataset_id, item_id, source_fields, question,
                                             max_characters_per_field=3000, max_total_characters=5000)

    dataset = Dataset.objects.get(id=dataset_id)

    prompt = item_relevancy_prompt.replace("{{ question }}", question)
    prompt = prompt.replace("{{ document }}", item_context)
    assert isinstance(dataset.merged_advanced_options, dict)
    dataset_context = dataset.merged_advanced_options.get("relevancy_context", prompts.dataset_context)
    prompt = prompt.replace("{{ dataset_context }}", dataset_context)

    # logging.warning(prompt)

    history = [ { "role": "system", "content": prompt } ]

    usage_tracker = ServiceUsage.get_usage_tracker(user_id, "External AI")
    result = usage_tracker.track_usage(0.1, f"judge item relevancy")
    if result["approved"]:
        if delay:
            time.sleep(delay / 1000)
        response_text = get_groq_response_using_history(history, GROQ_MODELS.LLAMA_3_70B)  # type: ignore
        assert response_text
        try:
            relevancy = json.loads(response_text)
        except (KeyError, ValueError):
            relevancy = {'error': 'Could not parse AI response'}
    else:
        relevancy = {'error': 'No AI check, usage limit exceeded'}
    if relevancy.get("explanation") and 'decision' in relevancy:
        item_relevancy_cache.set(cache_key, relevancy, expire=60*60*24*7)  # cache for 1 week
    return relevancy
