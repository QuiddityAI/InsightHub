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

from ..models import CollectionItem, DataCollection, Chat, Dataset, FieldType
from ..serializers import ChatSerializer, CollectionSerializer
from ..data_backend_client import get_item_question_context
from ..chatgpt_client import get_chatgpt_response_using_history

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

    chat.add_question(search_settings['all_field_query'])

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
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        chat_id: int = data["chat_id"]
        question: str = data["question"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    item.add_question(question)

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
def add_collection_extraction_question(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        name: str = data["name"]
        prompt: str = data["prompt"]
        source_fields: list = data["source_fields"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    if item.extraction_questions is None:
        item.extraction_questions = []  # type: ignore
    item.extraction_questions.append({'name': name, 'prompt': prompt, 'source_fields': source_fields})
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
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        question_name: str = data["question_name"]
        offset: int = data.get("offset", 0)
        limit: int = data.get("limit", -1)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    if collection.extraction_questions is None:
        return HttpResponse(status=400)
    question = [q for q in collection.extraction_questions if q['name'] == question_name]  # type: ignore
    if len(question) == 0:
        return HttpResponse(status=404)
    question = question[0]

    _extract_question_from_collection_class_items_thread(collection, class_name, question, offset, limit)

    data = CollectionSerializer(collection).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


def _extract_question_from_collection_class_items_thread(collection, class_name, question, offset, limit):
    collection.current_extraction_processes.append(question["name"])
    collection.save()
    def _run_safe():
        try:
            _extract_question_from_collection_class_items(collection, class_name, question, offset, limit)
        except Exception as e:
            logging.error(e)
        finally:
            collection.current_extraction_processes.remove(question["name"])
            collection.save()

    try:
        thread = threading.Thread(target=_run_safe)
        thread.start()
    except Exception as e:
        logging.error(e)
        collection.current_extraction_processes.remove(question["name"])
        collection.save()


def _extract_question_from_collection_class_items(collection, class_name, question, offset, limit):
    system_prompt = "Answer the following question based on the following document. " + \
        "Answer in one concise sentence, word or list. If the document does not contain the answer, " + \
        "answer with 'n/a'. If the answer is unclear, answer with '?'. \n\nQuestion:\n"
    system_prompt += question["prompt"] + "\n\nDocument:\n"
    collection_items = CollectionItem.objects.filter(collection=collection, is_positive=True, classes__contains=[class_name])
    collection_items = collection_items.order_by('-date_added')
    collection_items = collection_items[offset:offset+limit] if limit > 0 else collection_items[offset:]
    included_items = 0
    batch_size = 10
    for i in range(0, len(collection_items), batch_size):
        batch = collection_items[i:i+batch_size]
        _extract_question_from_collection_class_items_batch(batch, question, system_prompt)
        included_items += len(batch)
        if included_items % 100 == 0:
            logging.warning(f"Extracted {included_items} items for question {question['name']}.")

    logging.warning("Done extracting question from collection class items.")

def _extract_question_from_collection_class_items_batch(collection_items, question, system_prompt):
    def extract(item):
        if (item.extraction_answers or {}).get(question["name"]):
            return
        text = None
        if item.field_type == FieldType.TEXT:
            text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
        if item.field_type == FieldType.IDENTIFIER:
            assert item.dataset_id is not None
            assert item.item_id is not None
            text = get_item_question_context(item.dataset_id, item.item_id, question['source_fields'], question["prompt"])
        if not text:
            return
        prompt = system_prompt + text + "\n\nAnswer:\n"
        # logging.warning(prompt)
        history = [ { "role": "system", "content": prompt } ]
        response_text = get_chatgpt_response_using_history(history)
        #response_text = "n/a"
        # logging.warning(response_text)
        if item.extraction_answers is None:
            item.extraction_answers = {}  # type: ignore
        item.extraction_answers[question["name"]] = response_text
        item.save()

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(extract, collection_items)


@csrf_exempt
def remove_collection_class_extraction_results(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
        collection_id: int = data["collection_id"]
        class_name: str = data["class_name"]
        question_name: str = data["question_name"]
        offset: int = data.get("offset", 0)
        limit: int = data.get("limit", -1)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        collection = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if collection.created_by != request.user:
        return HttpResponse(status=401)

    if collection.extraction_questions is None:
        return HttpResponse(status=400)
    question = [q for q in collection.extraction_questions if q['name'] == question_name]  # type: ignore
    if len(question) == 0:
        return HttpResponse(status=404)
    question = question[0]

    collection_items = CollectionItem.objects.filter(collection=collection, classes__contains=[class_name])
    collection_items = collection_items.order_by('-date_added')
    collection_items = collection_items[offset:offset+limit] if limit > 0 else collection_items[offset:]
    for item in collection_items:
        if item.extraction_answers is None:
            continue
        if question_name in item.extraction_answers:
            del item.extraction_answers[question_name]
            item.save()

    return HttpResponse(None, status=204)
