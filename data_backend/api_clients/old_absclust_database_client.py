import math
import pickle
import os
from copy import deepcopy
import logging

from utils.helpers import run_in_batches

# import typesense
# ts_client = typesense.Client({
#     'api_key': os.getenv("ABSCLUST_TYPESENSE_DB_API_KEY"),
#     'nodes': [{
#         'host': os.getenv("ABSCLUST_TYPESENSE_DB_HOST"),
#         'port': '443',
#         'protocol': 'https'
#     }],
#     'connection_timeout_seconds': 2
# })

# removed this deprecated client for now to reduce dependencies
ts_client = None


app_config = {"TYPESENSE_PERPAGE": 100,
              "TYPESENSE_MAXPAGES": 20}


absclust_search_cache_path = "absclust_search_cache.pkl"


if os.path.exists(absclust_search_cache_path):
    with open(absclust_search_cache_path, "rb") as f:
        search_results_cache = pickle.load(f)
else:
    search_results_cache = dict()


def save_search_cache():
    with open(absclust_search_cache_path, "wb") as f:
        pickle.dump(search_results_cache, f)


def get_absclust_item_by_id(item_id: str):
    collection = ts_client.collections["articles"]
    doc = collection.documents[item_id].retrieve()
    return doc


def get_absclust_items_by_ids(item_ids: list[str]):
    collection = ts_client.collections["articles"]
    hits = run_in_batches(item_ids, 100, lambda items: collection.documents.search(
            dict(
                q = "*",
                filter_by = f"id:[{','.join(items)}]",
                per_page=len(items),
            )
        )["hits"])
    items = [a["document"] for a in hits]
    for item in items:
        if "title" not in item:
            item["title"] = "title unknown"
        if "abstract" not in item:
            item["abstract"] = ""
        item["_id"] = item["id"]
    return items


def get_absclust_search_results(query: str, additional_fields: list[str], limit: int):
    global search_results_cache

    if query + str(limit) in search_results_cache:
        # use deepcopy to prevent other methods overriding the content in the cache
        # because it would be passed as a reference
        return deepcopy(search_results_cache[query + str(limit)])

    collection = ts_client.collections["articles"]
    results_raw = []
    query_by = "abstract, title"
    filter_by = None
    sort_by = None
    params = {"q": query, "query_by": query_by, "filter_by": filter_by, "sort_by": sort_by}
    params = {k: v for k, v in params.items() if v is not None}
    hits = collection.documents.search(
        dict(
            **params,
            per_page=app_config["TYPESENSE_PERPAGE"],
            highlight_fields="",
            page=1,
        )
    )
    results_raw.extend(hits["hits"])
    total_pages = math.ceil(min(hits["found"], limit) / app_config["TYPESENSE_PERPAGE"])
    last_page_to_retrieve = min([total_pages, app_config["TYPESENSE_MAXPAGES"]])
    if last_page_to_retrieve > 1:
        for page in range(2, last_page_to_retrieve + 1):
            hits = collection.documents.search(
                dict(
                    **params,
                    per_page=app_config["TYPESENSE_PERPAGE"],
                    highlight_fields="",
                    page=page,
                )
            )
            results_raw.extend(hits["hits"])
    results_part = [a["document"] for a in results_raw[:limit]]
    for i, item in enumerate(results_part):
        if "title" not in item:
            item["title"] = "title unknown"
        if "abstract" not in item:
            item["abstract"] = ""
        item["_id"] = item["id"]

        item.update({
            '_score': 1.0,
            '_reciprocal_rank_score': 1.0 / (i + 1),
            '_origins': [{'type': 'absclust_db', 'field': 'unknown',
                          'query': query, 'score': 1.0, 'rank': i+1}],  #  TODO: get source score
        })

    search_results_cache[query + str(limit)] = results_part

    return deepcopy(results_part)
