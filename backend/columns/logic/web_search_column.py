import logging

from django.utils import timezone

from columns.logic.website_scraping_column import scrape_website_module
from columns.schemas import CellData


def google_search(input_data, source_fields) -> CellData:
    import requests
    from bs4 import BeautifulSoup

    search = input_data.get(source_fields[0], "")
    if not search:
        return CellData(
            value="No search query found",
            changed_at=timezone.now().isoformat(),
            is_computed=True,
        )

    url = "https://www.google.de/search"

    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82",
    }
    parameters = {"q": search}

    content = requests.get(url, headers=headers, params=parameters).text
    soup = BeautifulSoup(content, "html.parser")

    search = soup.find(id="search")
    first_link = search.find("a") if search else {}

    url = first_link.get("href") if first_link else ""  # type: ignore

    if not url:
        return CellData(
            value="No URL found",
            changed_at=timezone.now().isoformat(),
            is_computed=True,
        )

    return scrape_website_module({"url": url}, ["url"])
