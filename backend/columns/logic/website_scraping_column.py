import re
import os

from django.utils import timezone

from columns.schemas import CellData


def scrape_website_module(item, source_fields) -> CellData:
    import requests
    url = item.get(source_fields[0], "")
    if not url:
        return CellData(
            value="No URL found",
            changed_at=timezone.now().isoformat(),
            is_computed=True,
        )

    payload = {
        "url": url,
        "format": "markdown"
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('USE_SCRAPER_API_KEY')}",
        "Content-Type": "application/json"
    }

    scraper_url = "https://api.usescraper.com/scraper/scrape"
    response = requests.request("POST", scraper_url, json=payload, headers=headers)
    text = response.json().get("text", "")
    text = re.sub(r'(#+)(\S)', r'\1 \2', text)

    return CellData(
        collapsed_label=f"<i>Website Content<br>({len(text.split())} words)</i>",
        value=text,
        changed_at=timezone.now().isoformat(),
        is_computed=True,
    )


def scrape_website_module_plain(item, source_fields):
    url = item.get(source_fields[0], "")
    if not url:
        return {
            "value": "No URL found",
            "changed_at": timezone.now().isoformat(),
            "is_ai_generated": False,
            "is_computed": True,
            "is_manually_edited": False,
        }
    text = scrape_website_plain(url)
    return {
        "collapsed_label": f"<i>Website Content<br>({len(text.split())} words)</i>",
        "value": text,
        "changed_at": timezone.now().isoformat(),
        "is_ai_generated": False,
        "is_computed": True,
        "is_manually_edited": False,
    }


def scrape_website_plain(url):
    import requests
    headers = {
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
    }
    s = requests.Session()
    s.max_redirects = 3
    try:
        result = s.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        import logging
        logging.error(f"Error scraping website {url}: {e}")
        return ""
    html = result.text
    # rudimentary extraction of text from HTML
    text = ""
    in_tag = False
    for c in html:
        if c == "<":
            in_tag = True
        if not in_tag:
            text += c
        if c == ">":
            in_tag = False
    return text.strip()