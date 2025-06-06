import base64
import datetime
import json
import logging
import os
from multiprocessing.pool import ThreadPool
from typing import Callable

from requests import ReadTimeout

from config.utils import get_default_model
from data_map_backend.utils import DotDict
from ingest.logic.common import UPLOADED_FILES_FOLDER, store_thumbnail
from ingest.logic.pdferret_client import MetaInfo, extract_using_pdferret
from ingest.prompts import folder_summary_prompt
from ingest.schemas import (
    AiFileProcessingInput,
    AiFileProcessingOutput,
    AiMetadataResult,
    UploadedOrExtractedFile,
)

# from ingest.logic.video import process_video


def ai_file_processing_generator(input_items: list[dict], log_error: Callable, parameters: DotDict) -> list[dict]:
    results = {}
    target_field_value = True  # just storing that this item was processed
    file_batch = []
    folder_batch = []
    batch_size = 10
    document_language = parameters.get("document_language", "en")
    metadata_language = parameters.get("metadata_language", "en")

    def process_file_batch(batch: list[AiFileProcessingInput]):
        try:
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
            result = ai_file_processing_single(input_item, parsed_item, parameters)
            results[input_item.id] = [target_field_value, result.model_dump()]

    def process_folder_batch(batch: list[AiFileProcessingInput]):
        with ThreadPool(10) as pool:
            outputs = pool.map(lambda input_item: ai_file_processing_single_folder(input_item, parameters), batch)
        for input_item, output in zip(batch, outputs):
            results[input_item.id] = [target_field_value, output.model_dump()]

    for item in input_items:
        item = AiFileProcessingInput(**item)
        if item.is_folder:
            folder_batch.append(item)
        else:
            file_batch.append(item)
        if len(file_batch) >= batch_size:
            process_file_batch(file_batch)
            file_batch = []
        if len(folder_batch) >= batch_size:
            process_folder_batch(folder_batch)
            folder_batch = []
    if file_batch:
        process_file_batch(file_batch)
    if folder_batch:
        process_folder_batch(folder_batch)
    return [results[input_item["_id"]] for input_item in input_items]


def ai_file_processing_single(
    input_item: AiFileProcessingInput, parsed_data, parameters: DotDict
) -> AiFileProcessingOutput:
    file_metainfo: MetaInfo = parsed_data.metainfo

    # MetaInfo({'doi': '', 'title': ['Protokoll', 'Druck'], 'abstract': '',
    # 'authors': ['Georg T...', 'Klaus H...'], 'pub_date': ['2023-04-05T12:56:00Z',
    # '2023-04-11T07:13:20Z', '2013-08-07T11:41:02'], 'language': '',
    # 'file_features': FileFeatures(filename='...',
    # file='...', is_scanned=None), 'npages': None, 'thumbnail': b'\x89PNG...

    # try:
    #     from copy import deepcopy
    #     file_metainfo_copy = deepcopy(file_metainfo)
    #     file_metainfo_copy.thumbnail = None
    #     logging.warning(f"MetaInfo: {json.dumps(file_metainfo_copy, indent=2)}")
    # except Exception as e:
    #     logging.warning(f"Failed to log MetaInfo: {e}")

    # if not file_metainfo.title and not len(parsed_data.chunks):
    #     failed_files.append({"filename": uploaded_file.local_path, "reason": "no title or text found, skipping"})
    #     return None

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
    if full_text := parsed_data.get("full_text"):
        full_text = full_text
    else:
        full_text = " ".join([chunk["text"] for chunk in chunks[:max_chunks]])

    content_date = None
    if file_metainfo.mentioned_date:
        # making sure content_date is a valid date, otherwise OpenSearch will throw an error
        try:
            content_date = datetime.datetime.fromisoformat(file_metainfo.mentioned_date).date().isoformat()
        except ValueError:
            if len(file_metainfo.mentioned_date) == 4 and file_metainfo.mentioned_date.isdigit():
                content_date = f"{file_metainfo.mentioned_date}-01-01"
            else:
                logging.warning(f"Invalid date format: {file_metainfo.mentioned_date}")
    content_time = None
    # if file_metainfo.mentioned_time:
    #     # making sure content_time is a valid time, otherwise OpenSearch will throw an error
    #     try:
    #         content_time = datetime.time.fromisoformat(file_metainfo.mentioned_time).isoformat()
    #     except ValueError:
    #         logging.warning(f"Invalid time format: {file_metainfo.mentioned_time}")
    #         pass

    result = AiFileProcessingOutput(
        content_date=content_date,
        content_time=content_time,
        description=file_metainfo.search_description or "",
        document_language=file_metainfo.detected_language or parameters.get("document_language", "en"),
        full_text=full_text,
        full_text_chunks=chunks,
        summary=file_metainfo.abstract or "",
        thumbnail_path=(
            store_thumbnail(base64.decodebytes(file_metainfo.thumbnail.encode("utf-8")), input_item.uploaded_file_path)
            if file_metainfo.thumbnail and isinstance(file_metainfo.thumbnail, str)
            else None
        ),  # relative to UPLOADED_FILES_FOLDER
        title=file_metainfo.title or input_item.file_name,
        type_description=file_metainfo.document_type or "",
        people=file_metainfo.authors or [],
    )
    # if input_item.file_name.endswith(".mp4"):
    #     process_video(result, input_item)
    return result


def ai_file_processing_single_folder(input_item: AiFileProcessingInput, parameters: DotDict) -> AiFileProcessingOutput:
    prompt = folder_summary_prompt[parameters.get("metadata_language", "en")]
    prompt = prompt.replace("{{ context }}", input_item.full_text or "")
    description = get_default_model("small").generate_short_text(prompt, max_tokens=2000)

    return AiFileProcessingOutput(
        content_date=None,
        content_time=None,
        description=description or "",
        document_language=parameters.get("document_language", "en"),
        full_text=input_item.full_text or "",
        full_text_chunks=[],
        summary="",
        thumbnail_path=None,
        title=input_item.file_name,
        type_description="Ordner" if parameters.get("metadata_language", "en") == "en" else "Folder",
        people=[],
    )


def get_parent_folders(folder) -> list:
    if not folder:
        return []
    if folder == "/":
        return []
    if folder.endswith("/"):
        folder = folder[:-1]
    folders = folder.split("/")
    folders = ["/".join(folders[:i]) for i in range(len(folders), 0, -1)]
    folders = [f for f in folders if f]
    return folders


def import_office_document(
    files: list[UploadedOrExtractedFile], parameters: DotDict, on_progress=None
) -> tuple[list[dict], list[dict]]:
    if not files:
        return [], []

    if on_progress:
        on_progress(0.1)

    items = []
    for uploaded_file in files:
        folder = uploaded_file.metadata.folder if uploaded_file.metadata else None
        item = {
            "title": uploaded_file.original_filename,
            # "type_description": None,  # don't overwrite potentially already existing fields
            # "abstract": None,
            # "ai_tags": [],
            # "content_date": None,
            # "content_time": None,
            "language": parameters.get("document_language", "en"),
            # "thumbnail_path": None,  # relative to UPLOADED_FILES_FOLDER
            # "full_text": None,
            # "full_text_chunks": [],
            "file_created_at": uploaded_file.metadata.created_at if uploaded_file.metadata else None,
            "file_updated_at": uploaded_file.metadata.updated_at if uploaded_file.metadata else None,
            "file_name": uploaded_file.original_filename,
            "file_type": uploaded_file.local_path.split(".")[-1],
            "folder": folder,
            "full_path": os.path.join(folder or "", uploaded_file.original_filename),
            "uploaded_file_path": uploaded_file.local_path,  # relative to UPLOADED_FILES_FOLDER
            "parent_folders": get_parent_folders(folder),
            "is_folder": False,
        }
        items.append(item)
    failed_items = []
    return items, failed_items
