import logging
import math
import os
import time
from typing import Any, Iterable

import requests
from diskcache import Cache

from legacy_backend.logic.insert_logic import insert_many

SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
S2_API_URL = "https://api.semanticscholar.org/graph/v1"


cache = Cache("/data/quiddity_data/semantic_scholar_search_cache/")


# @cache.memoize(expire=3600*24*7*4)  # 4 weeks
def semantic_scholar_search_formatted(dataset_id: int, query: str, fields: Iterable[str] | None, limit: int = 2000):
    if not fields:
        fields = PAPER_SEARCH_FIELDS
    publication_types = None  # ["Journal", "Conference", "Preprint", "Patent", "Thesis", "Book"]
    open_access_pdf = False
    data, total = paper_bulk_search(query, limit, 0, fields, publication_types, open_access_pdf)
    logging.warning(f"Inserting {len(data)} Semantic Scholar results into dataset {dataset_id}")
    # the insert_many call also adds the _id field
    insert_many(dataset_id, data)
    for i, item in enumerate(data):
        score = 1.0 / (i + 1)
        item["_dataset_id"] = dataset_id
        item["_origins"] = [
            {"type": "semantic_scholar", "field": "unknown", "query": query, "score": score, "rank": i + 1}
        ]
        item["_score"] = score
        item["_reciprocal_rank_score"] = score
    sorted_ids = [e["_id"] for e in data]
    full_items = {e["_id"]: e for e in data}
    return sorted_ids, full_items


def paper_bulk_search(
    query: str,
    limit: int,
    offset: int,
    fields: Iterable[str] | None,
    publication_types: Iterable[str] | None,
    open_access_pdf: bool | None,
) -> tuple[list[dict[str, Any]], int]:
    all_items = []
    paging_token = None
    available_results = 0
    while len(all_items) == 0 or paging_token is not None:
        if len(all_items) > 0:
            # hacky workaround to avoid rate limit of 10 requests per second
            time.sleep(0.1)
        response = _paper_bulk_search_page(query, paging_token, fields, publication_types, open_access_pdf)
        available_results = response["total"]
        limit = min(limit, available_results - offset)
        items = response["data"]
        all_items.extend(items)
        paging_token = response.get("token")
        if len(all_items) >= limit:
            break

    tldrs = paper_batch_retrieval([x["paperId"] for x in all_items], ["tldr"])
    for i, item in enumerate(all_items):
        if item["paperId"] != tldrs[i]["paperId"]:
            raise ValueError(f"Paper ID mismatch: {item['paperId']} != {tldrs[i]['paperId']}")
        item["tldr"] = tldrs[i].get("tldr")
        if "abstract" not in item or not item["abstract"]:
            item["abstract"] = (tldrs[i].get("tldr") or {}).get("text")

    return all_items[:limit], available_results


def _paper_bulk_search_page(
    query: str,
    paging_token: str | None,
    fields: Iterable[str] | None,
    publication_types: Iterable[str] | None,
    open_access_pdf: bool | None,
) -> dict:
    params: dict = {
        "query": query,
    }
    if paging_token:
        params["token"] = paging_token
    if fields:
        params["fields"] = ",".join(fields)
    if publication_types:
        params["publicationTypes"] = ",".join(publication_types)
    if open_access_pdf:
        params["openAccessPdf"] = open_access_pdf
    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY}
    response = requests.get(
        f"{S2_API_URL}/paper/search/bulk",
        params=params,
        headers=headers,
    )
    try:
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Error in semantic_scholar_client._paper_relevance_search_page: {e}")
        logging.error(response.text)
        raise e
    return response.json()


def paper_batch_retrieval(paper_ids: list[str], fields: list[str]) -> list[dict[str, Any]]:
    per_page = 500
    pages = math.ceil(len(paper_ids) / float(per_page))
    all_results = []
    for page in range(pages):
        results = _paper_batch_retrieval_page(paper_ids[page * per_page : (page + 1) * per_page], fields)
        all_results.extend(results)
    return all_results


def _paper_batch_retrieval_page(paper_ids: list[str], fields: list[str]) -> list[dict[str, Any]]:
    if len(paper_ids) > 500:
        raise ValueError("The number of paper ids must be at most 500.")
    params = {
        "fields": ",".join(fields),
    }
    body = {"ids": paper_ids}
    headers = {"x-api-key": SEMANTIC_SCHOLAR_API_KEY}
    response = requests.post(
        f"{S2_API_URL}/paper/batch",
        params=params,
        headers=headers,
        json=body,
    )
    try:
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Error in semantic_scholar_client._paper_batch_retrieval: {e}")
        logging.error(response.text)
        raise e
    return response.json()


PAPER_SEARCH_FIELDS = [
    "abstract",
    "authors",
    "citationCount",
    "citationStyles",
    "corpusId",
    "externalIds",
    "fieldsOfStudy",
    "influentialCitationCount",
    "isOpenAccess",
    "journal",
    "openAccessPdf",
    "paperId",
    "publicationDate",
    "publicationTypes",
    "publicationVenue",
    "referenceCount",
    "s2FieldsOfStudy",
    "title",
    "url",
    "venue",
    "year",
]
