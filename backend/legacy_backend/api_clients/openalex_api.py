import json

import cachetools.func
import requests


@cachetools.func.ttl_cache(maxsize=128, ttl=60 * 60)  # seconds
def search_institution(query):
    url = f"https://api.openalex.org/institutions?select=id,display_name,relevance_score,works_count&search={query}"
    response = requests.get(url)
    institutions = response.json()
    return institutions


@cachetools.func.ttl_cache(maxsize=128, ttl=60 * 60)  # seconds
def get_dois_of_institution(institution_id, max_results=2000):
    cursor = "*"
    per_page = min(200, max_results)
    dois = []
    while cursor:
        url = f"https://api.openalex.org/works?select=doi&per-page={per_page}&cursor={cursor}&filter=authorships.institutions.lineage:{institution_id}"
        response = requests.get(url)
        new_dois = [e["doi"] for e in response.json()["results"]]
        if not new_dois:
            break
        dois.extend(new_dois)
        if len(dois) >= max_results:
            break
        cursor = response.json()["meta"].get("next_cursor")
    return dois[:max_results]


@cachetools.func.ttl_cache(maxsize=128, ttl=60 * 60)  # seconds
def get_ids_of_institution(institution_id, max_results=2000):
    cursor = "*"
    per_page = min(200, max_results)
    ids = []
    while cursor:
        url = f"https://api.openalex.org/works?select=id&per-page={per_page}&cursor={cursor}&filter=authorships.institutions.lineage:{institution_id}"
        response = requests.get(url)
        new_ids = [e["id"] for e in response.json()["results"]]
        if not new_ids:
            break
        ids.extend(new_ids)
        if len(ids) >= max_results:
            break
        cursor = response.json()["meta"].get("next_cursor")
    return ids[:max_results]


if __name__ == "__main__":
    institutions = search_institution("rostock")
    print(json.dumps(institutions, indent=2))
    institution_id = institutions["results"][0]["id"]

    results = get_dois_of_institution(institution_id)[:3]
    print(json.dumps(results, indent=2))
