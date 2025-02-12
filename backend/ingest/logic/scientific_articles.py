import base64
import csv
import logging
import uuid
from typing import Callable

from requests import ReadTimeout

from data_map_backend.utils import DotDict, pk_to_uuid_id
from ingest.logic.common import UPLOADED_FILES_FOLDER, store_thumbnail
from ingest.logic.pdferret_client import MetaInfo, extract_using_pdferret
from ingest.schemas import (
    AiFileProcessingInput,
    ScientificArticleProcessingOutput,
    UploadedOrExtractedFile,
)


def scientific_article_processing_generator(
    input_items: list[dict], log_error: Callable, parameters: DotDict
) -> list[dict]:
    results = {}
    target_field_value = True  # just storing that this item was processed
    file_batch = []
    batch_size = 10
    document_language = parameters.get("document_language", "en")
    metadata_language = parameters.get("metadata_language", "en")

    def process_file_batch(batch: list[AiFileProcessingInput]):
        try:
            # FIXME: need to set metadata_extractor to Grobid to get paper related metadata like doi
            parsed, failed = extract_using_pdferret(
                [f"{UPLOADED_FILES_FOLDER}/{input_item.uploaded_file_path}" for input_item in batch],
                doc_lang=document_language,
            )
        except ReadTimeout:
            logging.error("PDFerret timeout")
            failed = [DotDict({"file": item.uploaded_file_path, "exc": "pdferret timeout"}) for item in batch]
            parsed = [None] * len(batch)
        if failed:
            for failed_item in failed:
                if not failed_item:
                    continue
                # TODO: write the error in the description of the returned item?
                log_error(f"Failed to extract text from {failed_item.file}: {failed_item.exc}")
        assert len(parsed) == len(batch)  # TODO: handle failed items
        for parsed_item, input_item in zip(parsed, batch):
            if not parsed_item:
                results[input_item.id] = [target_field_value, None]
                continue
            result = scientific_article_processing_single(input_item, parsed_item, parameters)
            results[input_item.id] = [target_field_value, result.model_dump()]

    for item in input_items:
        item = AiFileProcessingInput(**item)
        file_batch.append(item)
        if len(file_batch) >= batch_size:
            process_file_batch(file_batch)
            file_batch = []

    if file_batch:
        process_file_batch(file_batch)

    return [results[input_item["_id"]] for input_item in input_items]


def scientific_article_processing_single(
    input_item: AiFileProcessingInput, parsed_data, parameters: DotDict
) -> ScientificArticleProcessingOutput:
    file_metainfo: MetaInfo = parsed_data.metainfo

    # OpenSearch has a limit of 32k characters per field:
    max_chars_per_chunk = 5000
    max_chunks = 100
    chunks = []
    for chunk in parsed_data.chunks:
        if not chunk["text"]:
            continue
        chunk["non_embeddable_content"] = None
        if len(chunk["text"]) > max_chars_per_chunk:
            chunk["text"] = chunk["text"][:max_chars_per_chunk] + "..."
        chunks.append(chunk)
    full_text = " ".join([chunk["text"] for chunk in chunks[:max_chunks]])

    try:
        date_str = file_metainfo.pub_date[0] if isinstance(file_metainfo.pub_date, list) else file_metainfo.pub_date
        publication_year = int(date_str.split("-")[0]) if file_metainfo.pub_date else None
    except ValueError:
        publication_year = None

    result = ScientificArticleProcessingOutput(
        doi=file_metainfo.doi,
        title=file_metainfo.title or input_item.file_name,
        abstract=file_metainfo.abstract,
        authors=file_metainfo.authors,
        journal="",
        publication_year=publication_year,
        cited_by=0,
        file_path=input_item.uploaded_file_path,  # relative to UPLOADED_FILES_FOLDER
        thumbnail_path=(
            store_thumbnail(base64.decodebytes(file_metainfo.thumbnail.encode("utf-8")), input_item.uploaded_file_path)
            if file_metainfo.thumbnail and isinstance(file_metainfo.thumbnail, str)
            else None
        ),  # relative to UPLOADED_FILES_FOLDER
        full_text=full_text,
        full_text_original_chunks=chunks,
    )
    return result


def scientific_article_pdf(
    files: list[UploadedOrExtractedFile], parameters: DotDict, on_progress=None
) -> tuple[list[dict], list[dict]]:
    if not files:
        return [], []

    if on_progress:
        on_progress(0.1)

    items = []
    for uploaded_file in files:
        item = {
            "id": pk_to_uuid_id(uploaded_file.local_path),
            "title": uploaded_file.original_filename,
            "file_path": uploaded_file.local_path,  # relative to UPLOADED_FILES_FOLDER
        }
        items.append(item)
    failed_items = []
    return items, failed_items


def _safe_to_int(s: str | None) -> int | None:
    if s is None:
        return None
    try:
        return int(s)
    except:
        return None


def scientific_article_csv(
    paths: list[UploadedOrExtractedFile], parameters, on_progress=None
) -> tuple[list[dict], list[dict]]:
    items = []
    for uploaded_file in paths:
        csv_reader = csv.DictReader(open(f"{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}", "r"))
        for i, row in enumerate(csv_reader):
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            try:
                items.append(
                    {
                        "id": row.get("doi") or pk_to_uuid_id(uploaded_file.local_path + str(i)),
                        "doi": row.get("doi"),
                        "title": row.get("title"),
                        "abstract": row.get("abstract"),
                        "authors": row.get("authors"),
                        "journal": row.get("journal"),
                        "publication_year": _safe_to_int(row.get("year")),
                        "cited_by": _safe_to_int(row.get("cited by")),
                        "file_path": None,
                        "thumbnail_path": None,
                        "full_text": None,
                        "full_text_original_chunks": [],
                    }
                )
            except Exception as e:
                logging.warning(f"Failed to parse row {i} in {uploaded_file.local_path}: {e}")
        if on_progress:
            on_progress(0.5 + (len(items) / len(paths)) * 0.5)

    return items, []


def scientific_article_form(raw_items, parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    for row in raw_items:
        try:
            items.append(
                {
                    "id": row.get("doi") or str(uuid.uuid4()),
                    "doi": row.get("doi"),
                    "title": row.get("title"),
                    "abstract": row.get("abstract"),
                    "authors": row.get("authors"),
                    "journal": row.get("journal"),
                    "publication_year": _safe_to_int(row.get("year")),
                    "cited_by": _safe_to_int(row.get("cited by")),
                    "file_path": None,
                    "thumbnail_path": None,
                    "full_text": None,
                    "full_text_original_chunks": [],
                }
            )
        except Exception as e:
            logging.warning(f"Failed to parse item: {e}")
        if on_progress:
            on_progress(0.5 + (len(items) / len(raw_items)) * 0.5)

    return items, []
