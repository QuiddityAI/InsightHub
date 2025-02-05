import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from ..models import ServiceUsage, User
from ..chatgpt_client import get_chatgpt_response_using_history, OPENAI_MODELS
from ..notifier import default_notifier

from .other_views import is_from_backend


@csrf_exempt
def convert_smart_query_to_parameters(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    # route is available without login

    try:
        data = json.loads(request.body)
        user_id: int | None = data.get("user_id")
        query: str = data["query"]
    except (KeyError, ValueError):
        return HttpResponse(status=400)

    system_prompt = """\
You are an expert in converting a natural language search \
query into a structured JSON document.

You only answer with a single JSON object of this schema:
{
    "query": "the main search query",
    "query_language": two letter language code like "en", "de", "fr", etc.,
    "search_type": one of ["keyword", "meaning", "hybrid"],
    "filters": [
        {
            "field": "field_name",
            "operator": one of ["contains", "does_not_contain", "is", "is_not", "gt", "lt", "gte", "lte"],
            "value": "value"
        },
    ],
}

Rules:
- If the search query is only about proper names, person names, or very specific words, use "keyword" as the search type.
- If the search query mostly consists of general words and could be phrased in multiple ways, use "meaning" as the search type.
- If the search query is a mix of both, use "hybrid" as the search type.
- If the search query mentions an exclusion of a word, use a filter with "does_not_contain" as the operator, the relevant field as "field", and the excluded word as "value".
- If the search query mentions an integer value being in a certain range, use appropriate operators like "gt", "lt", "gte", "lte".
- If the search query mentions a specific value for a field, use appropriate operators like "is", "is_not".
- If the search query looks like keywords, just use the original search query in the "query" field, except for the parts already converted to filters.
- If the search query is a full sentence but is about very specific things, use "keyword" as the search type and convert the sentence to a list of relevant keywords.
- If the search type "keyword" is used, remove any unnecessary words from the query like "show me", "find", "papers about ...", etc.
- If "meaning" is used as the search type, make sure that the "query" field is either a question or a sentence that could describe one of the items that should be found.
- The "query" field can be empty if only filters are needed.
- When in doubt about the language of the query, use "en" as the language code.
- "meaning" search only works for English queries. For other languages, use "keyword" search type.

Item type in this dataset: "paper" aka "publication" aka "article"

Available filter fields:
- "title"  // always use "contains" or "does_not_contain", not "is" or "is_not"
- "abstract"  // always use "contains" or "does_not_contain", not "is" or "is_not"
- "authors"  // always use "contains" or "does_not_contain", not "is" or "is_not"
- "publication_year"  // integer field

Examples:

Query: "mxene photocalytic papers after the year 2015"
JSON:
{
    "query": "mxene photocalytic",
    "query_language": "en",
    "search_type": "keyword",
    "filters": [
        {
            "field": "publication_year",
            "operator": "gt",
            "value": "2015"
        }
    ]
}

Query: "papers that are not about graphene"
JSON:
{
    "query": "",
    "query_language": "en",
    "search_type": "keyword",
    "filters": [
        {
            "field": "abstract",
            "operator": "does_not_contain",
            "value": "graphene"
        }
    ]
}

Query: "papers about the applications of graphene"
JSON:
{
    "query": "applications of graphene",
    "query_language": "en",
    "search_type": "hybrid",
    "filters": []
}

Query: "How can the material Mxene be used for solar cells?"
JSON:
{
    "query": "Mxene solar cells",
    "query_language": "en",
    "search_type": "hybrid",
    "filters": []
}

Query: "What are recent advances in the field of nanotechnology?"
JSON:
{
    "query": "An article about recent advances in nanotechnology",
    "query_language": "en",
    "search_type": "meaning",
    "filters": []
}

Query: "Show me papers about solar cells by John Doe"
JSON:
{
    "query": "An article about solar cells",
    "query_language": "en",
    "search_type": "meaning",
    "filters": [
        {
            "field": "authors",
            "operator": "contains",
            "value": "John Doe"
        }
    ]
}

Query: "Show me papers about nitrofluorene"
JSON:
{
    "query": "nitrofluorene",
    "query_language": "en",
    "search_type": "keyword",
    "filters": []
}

Query: "Welchen Einfluss haben Nanopartikel und ähnliches auf die Umwelt?"
JSON:
{
    "query": "Einfluss von Nanopartikeln auf die Umwelt",
    "query_language": "de",
    "search_type": "meaning",
    "filters": []
}
"""

    user_prompt = f"Query: {query}\nJSON:\n"

    # logging.warning(prompt)
    history = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    approved = False
    if user_id:
        usage_tracker = ServiceUsage.get_usage_tracker(user_id, "External AI")
        result = usage_tracker.track_usage(1, f"convert smart query to parameters")
        approved = result["approved"]
    else:
        # to enable new user to try the service, this method is available without login
        # (but the frontend makes sure that users need to login after the first usage)
        approved = True

    if approved:
        response_text = get_chatgpt_response_using_history(history, model=OPENAI_MODELS.GPT4)
    else:
        response_text = "AI usage limit exceeded."

    try:
        search_parameters = json.loads(response_text.strip().replace("```json", "").replace("```", ""))
    except json.JSONDecodeError:
        logging.error(f"Error in converting smart query to parameters: {response_text}")
        search_parameters = None

    result = json.dumps({"search_parameters": search_parameters})
    return HttpResponse(result, status=200, content_type="application/json")
