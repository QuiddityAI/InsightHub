import math
from typing import Any, Iterable
import os
import time
import requests
import logging

from diskcache import Cache
import requests
from bs4 import BeautifulSoup

from ..logic.insert_logic import insert_many

KLEINANZEIGEN_URL = ""


cache = Cache("/data/quiddity_data/kleinanzeigen_search_cache/")


#@cache.memoize(expire=3600*24*7*4)  # 4 weeks
def get_kleinanzeigen_results(dataset_id: int, query: str, limit: int, offset: int):

    data = _get_results(query, limit=limit, offset=offset)
    logging.warning(f"Inserting {len(data)} Semantic Scholar results into dataset {dataset_id}")
    # the insert_many call also adds the _id field
    insert_many(dataset_id, data)


    for i, item in enumerate(data):
        score = 1.0 / (i + 1)
        item["_dataset_id"] = dataset_id
        item["_origins"] = [{'type': 'kleinanzeigen', 'field': 'unknown',
                          'query': query, 'score': score, 'rank': i+1}]
        item["_score"] = score
        item["_reciprocal_rank_score"] = score
    sorted_ids = [e["_id"] for e in data]
    full_items = {e["_id"]: e for e in data}
    return sorted_ids, full_items


def _get_results(query: str, location: str | None='Berlin',
                 radius_km: int=0, min_price: int | None=None, max_price: int | None=None,
                 limit: int=25, offset: int=0) -> list[dict[str, Any]]:
    per_page = 25
    page = math.floor(offset / per_page) + 1
    url = f"https://www.kleinanzeigen.de/s-suchanfrage.html?keywords={query}&categoryId=&locationStr={location or ''}&locationId=&radius={radius_km}" + \
        f"&sortingField=SORTING_DATE&adType=&posterType=&pageNum={page}&action=find&maxPrice={max_price or ''}&minPrice={min_price or ''}&buyNowEnabled=false&shippingCarrier="
    all_items = []
    paging_token = None
    available_results = 0
    # TODO: paging

    logging.warning(f"Scraping {url}")
    html = _scrape(url)
    items = _extract_items(html)
    return items


def _extract_items(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.find_all('li', class_='ad-listitem')
    extracted_data = []

    for item in items:
        item_id = item.find('article')['data-adid'] if item.find('article') else None
        if not item_id:
            continue
        name = item.find('h2').text.strip()
        description = item.find('p', class_='aditem-main--middle--description').text.strip()
        image_url = item.find('meta', itemprop='contentUrl')['content']
        thumbnail_url = item.find('img')['src']
        url = 'https://www.kleinanzeigen.de' + item.find('a')['href']

        price = item.find('p', class_='aditem-main--middle--price-shipping--price')
        price = price.text.strip() if price else 'N/A'

        location = item.find('div', class_='aditem-main--top--left')
        location = location.text.strip() if location else 'N/A'

        time_posted = item.find('div', class_='aditem-main--top--right')
        time_posted = time_posted.text.strip() if time_posted else 'N/A'

        extracted_data.append({
            'item_id': item_id,
            'title': name,
            'description': description,
            'url': url,
            'image_url': image_url,
            'thumbnail_url': thumbnail_url,
            'price': price,
            'location': location,
            'time_posted': time_posted
        })

    return extracted_data


def _scrape(url):
    payload = {
        "url": url,
        "format": "html"
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('USE_SCRAPER_API_KEY')}",
        "Content-Type": "application/json"
    }

    scraper_url = "https://api.usescraper.com/scraper/scrape"
    response = requests.request("POST", scraper_url, json=payload, headers=headers)
    html = response.json().get("text", "")
    return html