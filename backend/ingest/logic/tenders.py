import logging
from typing import Callable
from multiprocessing.pool import ThreadPool

from ninja import Schema

from llmonkey.llms import BaseLLMModel, Google_Gemini_Flash_1_5_v1

from data_map_backend.utils import DotDict
from columns.logic.website_scraping_column import scrape_website_plain


class TenderInput(Schema):
    url: str | None = None
    website_text: str | None = None
    description: str | None = None


class TenderEnrichmentOutput(Schema):
    summary: str = ""
    website_text: str = ""



def tender_enrichment_generator(input_items: list[dict], log_error: Callable, parameters: DotDict) -> list[dict]:
    results = []
    target_field_value = True  # just storing that this item was processed
    batch = []
    batch_size = 5
    document_language = parameters.get("document_language", "en")
    metadata_language = parameters.get("metadata_language", "en")


    def process_batch(batch):
        with ThreadPool(5) as pool:
            new_results = pool.map(enrich_tender, batch)
        for result in new_results:
            results.append([target_field_value, result.model_dump()])

    for item in input_items:
        item = TenderInput(**item)
        batch.append(item)
        if len(batch) >= batch_size:
            process_batch(batch)
            batch = []
    if batch:
        process_batch(batch)
    return results


def enrich_tender(item: TenderInput) -> TenderEnrichmentOutput:
    if not item.url:
        return _summarize_description(item)
    for domain in domains_not_working_with_plain_scraping + domains_serving_pdfs + domains_needing_js:
        if item.url.startswith(domain):
            return _summarize_description(item)
    if item.website_text:
        website_text = item.website_text
    else:
        website_text, html = scrape_website_plain(item.url)
        if "work-in-progress-text" in html:
            # pages from cosinex GmbH don't work without JS and only serve PDF files
            return _summarize_description(item)
    if not website_text:
        return _summarize_description(item)
    model = Google_Gemini_Flash_1_5_v1()
    system_prompt = f"""Du bekommst vom Nutzer den HTML-Text der Webseite einer Ausschreibung.
    Fasse den Gegenstand der Ausschreibung und die zu erbringenden Leistungen in etwa 3-5 Sätzen zusammen.
    Wenn die Informationen nicht ausreichen, antworte nur mit "n/a"."""
    user_prompt = website_text[:10000]
    summary = model.generate_short_text(system_prompt=system_prompt, user_prompt=user_prompt) or "n/a"
    if summary == "n/a":
        return _summarize_description(item)
    return TenderEnrichmentOutput(summary=summary, website_text=website_text)


def _summarize_description(item: TenderInput) -> TenderEnrichmentOutput:
    if not item.description:
        return TenderEnrichmentOutput(summary="", website_text="")
    model = Google_Gemini_Flash_1_5_v1()
    system_prompt = f"""Du bekommst vom Nutzer eine Beschreibung der Ausschreibung.
    Fasse den Gegenstand der Ausschreibung und die zu erbringenden Leistungen in etwa 3-5 Sätzen zusammen.
    Wenn die Informationen nicht ausreichen, antworte mit "n/a"."""
    user_prompt = item.description[:10000]
    summary = model.generate_short_text(system_prompt=system_prompt, user_prompt=user_prompt) or "n/a"
    if summary == "n/a":
        summary = ""
    return TenderEnrichmentOutput(summary=summary, website_text=item.description)


domains_working_with_plain_scraping = [
    "https://www.evergabe-online.de",
    "https://www.sachsen-vergabe.de",
]

domains_not_working_with_plain_scraping = [
    "https://www.vergabe.metropoleruhr.de",
    "https://www.deutsche-evergabe.de",
    "https://www.staatsanzeiger-eservices.de"
]

domains_serving_pdfs = [
    # anything from cosinex GmbH
]

domains_needing_js = [
    "https://www.deutsches-ausschreibungsblatt.de/",
]
