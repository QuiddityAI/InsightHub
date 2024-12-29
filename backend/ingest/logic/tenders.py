import logging
import os
import json
import base64
import datetime
from typing import Callable
from multiprocessing.pool import ThreadPool

from ninja import Schema

from llmonkey.llms import BaseLLMModel, Google_Gemini_Flash_1_5_v1
from requests import ReadTimeout

from data_map_backend.utils import DotDict
from ingest.schemas import UploadedOrExtractedFile, AiMetadataResult, AiFileProcessingInput, AiFileProcessingOutput
from ingest.logic.common import UPLOADED_FILES_FOLDER, store_thumbnail
from ingest.logic.pdferret_client import extract_using_pdferret
# from ingest.logic.video import process_video
from columns.logic.website_scraping_column import scrape_website_plain


class TenderInput(Schema):
    url: str | None = None


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
        return TenderEnrichmentOutput(summary="No URL found", website_text="")
    text = scrape_website_plain(item.url)
    summary = "Couldn't extract text from the website"
    if text:
        model = Google_Gemini_Flash_1_5_v1()
        system_prompt = f"""Du bekommst vom Nutzer den HTML-Text der Webseite einer Ausschreibung.
        Fasse den Gegenstand der Ausschreibung und die zu erbringenden Leistungen in etwa 3-5 Sätzen zusammen."""
        user_prompt = text
        summary = model.generate_short_text(system_prompt=system_prompt, user_prompt=user_prompt) or ""
    return TenderEnrichmentOutput(summary=summary, website_text=text)
