import json
import logging
import time

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from diskcache import Cache

from data_map_backend.models import DataCollection, Chat, Dataset, ServiceUsage, User
from data_map_backend.serializers import ChatSerializer
from data_map_backend.data_backend_client import get_item_question_context
from data_map_backend.chatgpt_client import OPENAI_MODELS, get_chatgpt_response_using_history
from data_map_backend.groq_client import GROQ_MODELS, get_groq_response_using_history
from data_map_backend.prompts import search_question_prompt, item_relevancy_prompt
from data_map_backend import prompts
from data_map_backend.notifier import default_notifier

from .other_views import is_from_backend


@csrf_exempt
def create_chat_from_search_settings(request):
    if request.method != "POST":
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
        name=search_settings["all_field_query"],
    )

    chat.add_question(search_settings["all_field_query"], request.user.id)

    data = ChatSerializer(chat).data
    return HttpResponse(json.dumps(data), content_type="application/json", status=201)


@csrf_exempt
def add_collection_class_chat(request):
    if request.method != "POST":
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
    if request.method != "POST":
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
    if request.method != "POST":
        return HttpResponse(status=405)
    if not request.user.is_authenticated and not is_from_backend(request):
        return HttpResponse(status=401)

    try:
        data = json.loads(request.body)
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    chats = Chat.objects.filter(created_by=request.user.id, collection__isnull=True)
    chats = chats.order_by("-created_at")
    chat_ids = [{"id": chat.id, "name": chat.name} for chat in chats]  # type: ignore

    return HttpResponse(json.dumps(chat_ids), content_type="application/json", status=200)


@csrf_exempt
def get_collection_class_chats(request):
    if request.method != "POST":
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
    chats = chats.order_by("-created_at")
    chat_ids = [{"id": chat.id, "name": chat.name} for chat in chats]  # type: ignore

    return HttpResponse(json.dumps(chat_ids), content_type="application/json", status=200)


@csrf_exempt
def get_chat_by_id(request):
    if request.method != "POST":
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
    if request.method != "POST":
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
def track_service_usage(request):
    if request.method != "POST":
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
    if request.method != "POST":
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
        "usage_current_period": usage_tracker.get_current_period().usage,
        "limit_per_period": usage_tracker.limit_per_period,
        "period_type": usage_tracker.period_type,
    }

    return HttpResponse(json.dumps(result), content_type="application/json", status=200)


@csrf_exempt
def answer_question_using_items(request):
    if request.method != "POST":
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
        text = f"Document ID: [{ds_id}, {item_id}]\n" + get_item_question_context(
            ds_id, item_id, source_fields, question
        )
        texts.append(text)

    context = "\n\n".join(texts)

    prompt = search_question_prompt.replace("{{ context }}", context).replace("{{ question }}", question)

    history = [{"role": "system", "content": prompt}]

    response_text = get_chatgpt_response_using_history(history, OPENAI_MODELS.GPT4_O)

    return HttpResponse(
        json.dumps({"answer": response_text, "prompt": prompt}), content_type="application/json", status=200
    )


@csrf_exempt
def judge_item_relevancy_using_llm(request):
    if request.method != "POST":
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


def _judge_item_relevancy_using_llm(
    user_id: int, question: str, dataset_id: int, item_id: str, delay: int = 0
) -> dict:
    global item_relevancy_cache
    if not item_relevancy_cache:
        # create it here and note above, as otherwise it would also be created when management commands are run
        # and in this case it might not be from the docker container and the /data/ folder might not be available
        item_relevancy_cache = Cache("/data/quiddity_data/item_relevancy_cache/")
    cache_key = f"{question}_{dataset_id}_{item_id}"
    if cache_key in item_relevancy_cache:
        return item_relevancy_cache.get(cache_key)  # type: ignore

    source_fields = ["_descriptive_text_fields", "_full_text_snippets"]
    item_context = get_item_question_context(
        dataset_id, item_id, source_fields, question, max_characters_per_field=3000, max_total_characters=5000
    )

    dataset = Dataset.objects.get(id=dataset_id)

    prompt = item_relevancy_prompt.replace("{{ question }}", question)
    prompt = prompt.replace("{{ document }}", item_context)
    assert isinstance(dataset.merged_advanced_options, dict)
    dataset_context = dataset.merged_advanced_options.get("relevancy_context", prompts.dataset_context)
    prompt = prompt.replace("{{ dataset_context }}", dataset_context)

    # logging.warning(prompt)

    history = [{"role": "system", "content": prompt}]

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
            relevancy = {"error": "Could not parse AI response"}
    else:
        relevancy = {"error": "No AI check, usage limit exceeded"}
    if relevancy.get("explanation") and "decision" in relevancy:
        item_relevancy_cache.set(cache_key, relevancy, expire=60 * 60 * 24 * 7)  # cache for 1 week
    return relevancy
