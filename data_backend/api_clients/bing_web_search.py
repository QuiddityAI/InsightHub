from functools import lru_cache
import os
import time
import requests
import logging

from diskcache import Cache

from logic.insert_logic import insert_many
from utils.helpers import load_env_file

load_env_file()

bing_subscription_key = os.environ.get('BING_SEARCH_V7_SUBSCRIPTION_KEY', '')
bing_web_search_endpoint = os.environ.get('BING_SEARCH_V7_ENDPOINT', '') + "/v7.0/search"


cache = Cache("/data/quiddity_data/bing_web_search_cache/")

@cache.memoize(expire=3600*24*7*4)  # 4 weeks
def bing_web_search_formatted(dataset_id: int, query: str, website_filter: str | None = None, limit: int = 300):
    data = bing_web_search(query, website_filter, limit)
    # TODO: remove unused and distracting fields (e.g. "id" that is only valid for this query)
    logging.warning(f"Inserting {len(data)} Bing web results into dataset {dataset_id}")
    # _id field is added in insert_many:
    insert_many(dataset_id, data)
    for i, item in enumerate(data):
        score = 1.0 / (i + 1)
        item["_dataset_id"] = dataset_id
        item["_origins"] = [{'type': 'web_search', 'field': 'unknown',
                          'query': query, 'score': score, 'rank': i+1}]
        item["_score"] = score
        item["_reciprocal_rank_score"] = score
    sorted_ids = [e["_id"] for e in data]
    full_items = {e["_id"]: e for e in data}
    return sorted_ids, full_items


@lru_cache
def bing_web_search(query: str, website_filter: str | None = None, limit: int = 50):
    per_page = 50  # maximum allowed by Bing
    results = []
    while len(results) < limit:
        if len(results) > 0:
            # hacky workaround to avoid rate limit of 3 requests per second
            time.sleep(0.33)
        # the API doesn't always return the number of requested results even if there are more
        # (and it might also return more results than requested)
        partial_results = bing_web_search_call(query, website_filter, min(per_page, limit - len(results)), len(results))
        results += partial_results
        logging.warning(f"bing_web_search: {len(results)} results so far")
        if len(partial_results) == 0:
            break
    results = results[:limit]
    for item in results:
        # query needs to be part of id because snippet is query specific
        item["snippet_id"] = item["url"] + f"_{query}"
    return results


def bing_web_search_call(query: str, website_filter: str | None = None, limit: int = 50, offset: int = 0) -> list:
    if website_filter:
        query = f'site:{website_filter} {query}'
    market = 'en-US'
    params = {
              'q': query,
              'mkt': market,
              'count': limit,
              'offset': offset,
              'responseFilter': 'Webpages'
              }
    headers = { 'Ocp-Apim-Subscription-Key': bing_subscription_key }

    try:
        response = requests.get(bing_web_search_endpoint, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logging.error(err)
        logging.error(err.response.text)
        return []
    if 'webPages' not in response.json():
        logging.error(response.json())
        return []

    logging.warning(f"Estimated number of results: {response.json()['webPages']['totalEstimatedMatches']}, {limit} {offset}")
    data = response.json()['webPages']['value']
    return data
