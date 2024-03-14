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

from .models import CollectionItem, DataCollection, CollectionChat, Dataset, FieldType
from .serializers import CollectionChatSerializer, CollectionSerializer
from .data_backend_client import data_backend_url, get_item_by_id
from .chatgpt_client import get_chatgpt_response_using_history

from .views import is_from_backend


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

    chat = CollectionChat.objects.create(
        collection=item,
        class_name=class_name,
        name=chat_name
    )

    data = CollectionChatSerializer(chat).data
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
        item = CollectionChat.objects.get(id=chat_id)
    except CollectionChat.DoesNotExist:
        return HttpResponse(status=404)
    if item.collection.created_by != request.user:
        return HttpResponse(status=401)

    item.add_question(question)

    data = CollectionChatSerializer(item).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


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

    chats = CollectionChat.objects.filter(collection_id=collection_id, class_name=class_name)
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
        item = CollectionChat.objects.get(id=chat_id)
    except CollectionChat.DoesNotExist:
        return HttpResponse(status=404)
    if item.collection.created_by != request.user:
        return HttpResponse(status=401)

    data = CollectionChatSerializer(item).data
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
    item.extraction_questions.append({'name': name, 'prompt': prompt})
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
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    try:
        item = DataCollection.objects.get(id=collection_id)
    except DataCollection.DoesNotExist:
        return HttpResponse(status=404)
    if item.created_by != request.user:
        return HttpResponse(status=401)

    if item.extraction_questions is None:
        return HttpResponse(status=400)
    question = [q for q in item.extraction_questions if q['name'] == question_name]  # type: ignore
    if len(question) == 0:
        return HttpResponse(status=404)
    question = question[0]

    _extract_question_from_collection_class_items_thread(item, class_name, question)

    data = CollectionSerializer(item).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=200)


def _extract_question_from_collection_class_items_thread(collection, class_name, question):
    collection.current_extraction_processes.append(question["name"])
    collection.save()
    def _run_safe():
        try:
            _extract_question_from_collection_class_items(collection, class_name, question)
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


def _extract_question_from_collection_class_items(collection, class_name, question):
    system_prompt = "Answer the following question based on the following JSON document. " + \
        "Answer in one concise sentence, word or list. If the document does not contain the answer, " + \
        "answer with 'n/a'. If the answer is unclear, answer with '?'. \n\n"
    system_prompt += question["prompt"] + "\n\nDocument:\n"
    collection_items = CollectionItem.objects.filter(collection=collection)
    included_items = 0
    for item in collection_items:
        if not item.is_positive:
            continue
        if class_name not in item.classes:
            continue
        text = None
        if item.field_type == FieldType.TEXT:
            text = json.dumps({"_id": item.id, "text": item.value}, indent=2)  # type: ignore
        if item.field_type == FieldType.IDENTIFIER:
            ds_id, item_id = json.loads(item.value)  # type: ignore
            fields = list(Dataset.objects.get(id=ds_id).descriptive_text_fields.all().values_list("identifier", flat=True))
            fields.append("_id")
            full_item = get_item_by_id(ds_id, item_id, fields)
            text = json.dumps(full_item, indent=2)
        if not text:
            continue
        prompt = system_prompt + text
        logging.warning(prompt)
        history = [ { "role": "system", "content": prompt } ]
        response_text = get_chatgpt_response_using_history(history)
        logging.warning(response_text)
        if item.extraction_answers is None:
            item.extraction_answers = {}  # type: ignore
        item.extraction_answers[question["name"]] = response_text
        item.save()
        included_items += 1
        if included_items > 5:
            break

    logging.warning("Done extracting question from collection class items.")


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

    collection_items = CollectionItem.objects.filter(collection=collection)
    for item in collection_items:
        if class_name not in item.classes:
            continue
        if item.extraction_answers is None:
            continue
        if question_name in item.extraction_answers:
            del item.extraction_answers[question_name]
            item.save()

    return HttpResponse(None, status=204)
