from multiprocessing.pool import ThreadPool
from typing import Callable

from ninja import Schema

from columns.logic.website_scraping_column import scrape_website_plain
from data_map_backend.utils import DotDict
import dspy
from config.utils import get_default_dspy_llm


class TenderSummarySignature:
    """You receive the description and text of a tender web page from the user.
    Summarize the subject of the tender and the services to be provided in about 2-3 sentences.
    If the information is not sufficient or the text only contains error messages, answer with "n/a".
    Answer must be in German."""

    description: str = dspy.InputField()
    website_text: str = dspy.InputField()
    summary: str = dspy.OutputField()


tender_summary = dspy.Predict(TenderSummarySignature)


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
    batch_size = 10
    document_language = parameters.get("document_language", "en")
    metadata_language = parameters.get("metadata_language", "en")

    def process_batch(batch):
        with ThreadPool(batch_size) as pool:
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


def _summarize_tender_information(item: TenderInput, website_text: str | None = None) -> TenderEnrichmentOutput:
    if not item.description and not website_text:
        return TenderEnrichmentOutput(summary="", website_text="")
    model = get_default_dspy_llm("tender_summary")
    with dspy.context(lm=dspy.LM(**model.to_litellm())):
        summary = tender_summary(
            description=item.description[:10000] if item.description else "n/a",
            website_text=website_text[:10000] if website_text else "n/a",
        ).summary

    if summary == "n/a":
        summary = ""

    return TenderEnrichmentOutput(summary=summary, website_text=website_text or "", services="", requirements="")


# evergabe.de: paywall, aber infos sind in <pre> auf service.bund.de

domains_working_with_plain_scraping = [
    "https://www.evergabe-online.de",
    "https://www.sachsen-vergabe.de",
    "https://plattform.aumass.de",
]

domains_not_working_with_plain_scraping = [
    "https://www.vergabe.metropoleruhr.de",
    "https://www.deutsche-evergabe.de",
    "https://www.staatsanzeiger-eservices.de",
]

domains_serving_pdfs = [
    # anything from cosinex GmbH
]

domains_needing_js = [
    "https://www.deutsches-ausschreibungsblatt.de/",
]
