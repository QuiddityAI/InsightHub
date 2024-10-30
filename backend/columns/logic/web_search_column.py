import logging

from django.utils import timezone

from columns.logic.website_scraping_column import scrape_website_module



def google_search(input_data, source_fields):
    from bs4 import BeautifulSoup
    import requests

    search = input_data.get(source_fields[0], "")
    if not search:
        return {
            "value": "No search query found",
            "changed_at": timezone.now().isoformat(),
            "is_ai_generated": False,
            "is_computed": True,
            "is_manually_edited": False,
        }

    url = 'https://www.google.de/search'

    headers = {
        'Accept' : '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82',
    }
    parameters = {'q': search}

    content = requests.get(url, headers = headers, params = parameters).text
    soup = BeautifulSoup(content, 'html.parser')

    search = soup.find(id = 'search')
    first_link = search.find('a') if search else {}

    url = first_link.get('href') if first_link else ""  # type: ignore

    if not url:
        return {
            "value": "No URL found",
            "changed_at": timezone.now().isoformat(),
            "is_ai_generated": False,
            "is_computed": True,
            "is_manually_edited": False,
        }

    return scrape_website_module({"url": url}, ["url"])