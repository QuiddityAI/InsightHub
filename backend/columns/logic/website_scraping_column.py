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
    import requests
    url = item.get(source_fields[0], "")
    if not url:
        return {
            "value": "No URL found",
            "changed_at": timezone.now().isoformat(),
            "is_ai_generated": False,
            "is_computed": True,
            "is_manually_edited": False,
        }
    headers = {'headers':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}
    result = requests.get(url, headers=headers)
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
    return {
        "collapsed_label": f"<i>Website Content<br>({len(text.split())} words)</i>",
        "value": text,
        "changed_at": timezone.now().isoformat(),
        "is_ai_generated": False,
        "is_computed": True,
        "is_manually_edited": False,
    }