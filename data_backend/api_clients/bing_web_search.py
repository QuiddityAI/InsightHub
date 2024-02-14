import json
import os
import time
import requests
import logging

with open(".env", "r") as f:
    for line in f:
        if line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.strip().split("=")
        os.environ[key] = value

bing_subscription_key = os.environ.get('BING_SEARCH_V7_SUBSCRIPTION_KEY', '')
bing_web_search_endpoint = os.environ.get('BING_SEARCH_V7_ENDPOINT', '') + "/v7.0/search"


def bing_web_search_formatted(dataset, query: str, website_filter: str | None = None, limit: int = 300):
    data = bing_web_search(query, website_filter, limit)
    for i, item in enumerate(data):
        score = 1.0 / (i + 1)
        item["_id"] = item["url"]
        item["_dataset_id"] = dataset.id,
        item["_origins"] = [{'type': 'web_search', 'field': 'unknown',
                          'query': query, 'score': score, 'rank': i+1}]
        item["_score"] = score
        item["_reciprocal_rank_score"] = score
    sorted_ids = [e["url"] for e in data]
    full_items = {e["url"]: e for e in data}
    return sorted_ids, full_items


def bing_web_search(query: str, website_filter: str | None = None, limit: int = 50):
    per_page = 50  # maximum allowed by Bing
    results = []
    while len(results) < limit:
        if len(results) > 0:
            # hacky workaround to avoid rate limit of 3 requests per second
            time.sleep(0.33)
        # the API doesn't always return the number of requested results even if there are more
        partial_results = bing_web_search_call(query, website_filter, min(per_page, limit - len(results)), len(results))
        results += partial_results
        logging.warning(f"bing_web_search: {len(results)} results so far")
        if len(partial_results) == 0:
            break
    return results


def bing_web_search_call(query: str, website_filter: str | None = None, limit: int = 50, offset: int = 0) -> list:
    if website_filter:
        query += f'+site:{website_filter}'
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

    logging.warning(f"Estimated number of results: {response.json()['webPages']['totalEstimatedMatches']}, {limit} {offset}")
    data = response.json()['webPages']['value']
    return data
