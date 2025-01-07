import logging
from typing import Callable
from multiprocessing.pool import ThreadPool

from ninja import Schema

from llmonkey.llms import BaseLLMModel, Nebius_Llama_3_1_8B_cheap

from data_map_backend.utils import DotDict
from columns.logic.website_scraping_column import scrape_website_plain

LlmModel = Nebius_Llama_3_1_8B_cheap


class TenderInput(Schema):
    url: str | None = None
    website_text: str | None = None
    description: str | None = None


class TenderEnrichmentOutput(Schema):
    summary: str = ""
    services: str = ""  # aka Leistungsverzeichnis
    requirements: str = ""  # aka Anforderungen
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
        return _summarize_tender_information(item)
    for domain in domains_not_working_with_plain_scraping + domains_serving_pdfs + domains_needing_js:
        if item.url.startswith(domain):
            return _summarize_tender_information(item)
    if item.website_text:
        website_text = item.website_text
    else:
        if item.url.startswith("https://www.dtvp.de/Satellite/notice/"):
            # https://www.dtvp.de/Satellite/notice/CXP4DCCH7ES ->
            # https://www.dtvp.de/Satellite/public/company/project/CXP4DCCH7ES/de/processdata/eforms"
            item.url = item.url.replace("/notice/", "/public/company/project/") + "/de/processdata/eforms"
        website_text, html = scrape_website_plain(item.url)
    if not website_text:
        return _summarize_tender_information(item)
    return _summarize_tender_information(item, website_text)


def _summarize_tender_information(item: TenderInput, website_text: str | None=None) -> TenderEnrichmentOutput:
    if not item.description and not website_text:
        return TenderEnrichmentOutput(summary="", website_text="")
    model = LlmModel()
    user_prompt = f"Beschreibung:\n{item.description[:10000] if item.description else 'n/a' or 'n/a'}\n\nWebsite Text:\n{website_text[:10000] if website_text else 'n/a' or 'n/a'}"

    system_prompt = f"""Du bekommst vom Nutzer die Beschreibung und den Text einer Webseite einer Ausschreibung.
    Fasse den Gegenstand der Ausschreibung und die zu erbringenden Leistungen in etwa 2-3 Sätzen zusammen.
    Wenn die Informationen nicht ausreichen oder der Text nur Fehlermeldungen beinhaltet, antworte mit "n/a"."""
    summary = model.generate_short_text(system_prompt=system_prompt, user_prompt=user_prompt) or "n/a"
    if summary == "n/a":
        summary = ""

    system_prompt = f"""Du bekommst vom Nutzer die Beschreibung und den Text einer Webseite einer Ausschreibung.
    Fasse die zu erbringenden Leistungen in kurzen Stichpunkten zusammen. Lasse andere Informationen weg.
    Wenn die Informationen nicht ausreichen oder der Text nur Fehlermeldungen beinhaltet, antworte mit "n/a"."""
    services = model.generate_short_text(system_prompt=system_prompt, user_prompt=user_prompt) or "n/a"
    if services == "n/a":
        services = ""

    system_prompt = f"""Du bekommst vom Nutzer die Beschreibung und den Text einer Webseite einer Ausschreibung.
    Fasse die Anforderungen an den Bieter in kurzen Stichpunkten zusammen. Lasse andere Informationen weg.
    Wenn die Informationen nicht ausreichen oder der Text nur Fehlermeldungen beinhaltet, antworte mit "n/a"."""
    requirements = model.generate_short_text(system_prompt=system_prompt, user_prompt=user_prompt) or "n/a"
    if requirements == "n/a":
        requirements = ""

    return TenderEnrichmentOutput(summary=summary, website_text=website_text or "", services=services, requirements=requirements)


# evergabe.de: paywall, aber infos sind in <pre> auf service.bund.de

domains_working_with_plain_scraping = [
    "https://www.evergabe-online.de",
    "https://www.sachsen-vergabe.de",
    "https://plattform.aumass.de",
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
