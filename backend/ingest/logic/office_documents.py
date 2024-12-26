import logging
import os
import json
import base64
import datetime
from typing import Callable

from llmonkey.llms import BaseLLMModel, Google_Gemini_Flash_1_5_v1
from requests import ReadTimeout

from data_map_backend.utils import DotDict
from ingest.schemas import UploadedOrExtractedFile, AiMetadataResult, AiFileProcessingInput, AiFileProcessingOutput
from ingest.logic.common import UPLOADED_FILES_FOLDER, store_thumbnail
from ingest.logic.pdferret_client import extract_using_pdferret
# from ingest.logic.video import process_video


def ai_file_processing_generator(input_items: list[dict], log_error: Callable, parameters: DotDict) -> list[dict]:
    results = []
    target_field_value = True  # just storing that this item was processed
    batch = []
    batch_size = 10
    document_language = parameters.get("document_language", "en")
    metadata_language = parameters.get("metadata_language", "en")

    def process_batch(batch):
        try:
            parsed, failed = extract_using_pdferret([f'{UPLOADED_FILES_FOLDER}/{input_item.uploaded_file_path}' for input_item in batch], doc_lang=document_language)
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
                results.append([target_field_value, None])
                continue
            result = ai_file_processing_single(input_item, parsed_item, parameters)
            results.append([target_field_value, result.model_dump()])

    for item in input_items:
        item = AiFileProcessingInput(**item)
        batch.append(item)
        if len(batch) >= batch_size:
            process_batch(batch)
            batch = []
    if batch:
        process_batch(batch)
    return results


def ai_file_processing_single(input_item: AiFileProcessingInput, parsed_data, parameters: DotDict) -> AiFileProcessingOutput:
    file_metainfo = parsed_data.metainfo

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
        if not chunk['text']:
            continue
        chunk['non_embeddable_content'] = None
        if len(chunk['text']) > max_chars_per_chunk:
            chunk['text'] = chunk['text'][:max_chars_per_chunk] + "..."
        chunks.append(chunk)
    full_text = " ".join([chunk['text'] for chunk in chunks[:max_chunks]])

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
        thumbnail_path=store_thumbnail(base64.decodebytes(file_metainfo.thumbnail.encode('utf-8')),
                                       input_item.uploaded_file_path) if file_metainfo.thumbnail else None,  # relative to UPLOADED_FILES_FOLDER
        title=file_metainfo.title or input_item.file_name,
        type_description=file_metainfo.document_type or "",
        people=file_metainfo.authors or [],
    )
    # if input_item.file_name.endswith(".mp4"):
    #     process_video(result, input_item)
    return result


def import_office_document(files: list[UploadedOrExtractedFile], parameters: DotDict, on_progress=None) -> tuple[list[dict], list[dict]]:
    if not files:
        return [], []

    if on_progress:
        on_progress(0.1)

    items = []
    for uploaded_file in files:
        folder = uploaded_file.metadata.folder if uploaded_file.metadata else None
        item = {
            "title": uploaded_file.original_filename,
            "type_description": None,
            "abstract": None,
            "ai_tags": [],
            "content_date": None,
            "content_time": None,
            "language": parameters.get("document_language", "en"),
            "thumbnail_path": None,  # relative to UPLOADED_FILES_FOLDER
            "full_text": None,
            "full_text_chunks": [],
            "file_created_at": uploaded_file.metadata.created_at if uploaded_file.metadata else None,
            "file_updated_at": uploaded_file.metadata.updated_at if uploaded_file.metadata else None,
            "file_name": uploaded_file.original_filename,
            "file_type": uploaded_file.local_path.split(".")[-1],
            "folder": folder,
            "full_path": os.path.join(folder or "", uploaded_file.original_filename),
            "uploaded_file_path": uploaded_file.local_path,  # relative to UPLOADED_FILES_FOLDER
        }
        items.append(item)
    failed_items = []
    return items, failed_items


def get_ai_summary(title: str, folder: str | None, full_text: str) -> AiMetadataResult | None:
    prompt = """
You are an expert in extracting titles and short summaries from documents.
The available information about the document start with <document> and end with </document>.

<document>
Folder: {{ folder }}
File Name: {{ title }}
Content: {{ content }}
</document>

Try to extract the title (keep it close to what is mentioned in the document, and its not necessarily the file name), the abstract document type and a one-sentence summary of the content as a JSON object.
The abstract document type should be something like: "paper about a new algorithm", "report about a waste plant", "presentation about a new product".
The summary should be a single sentence that captures the essence of the document.
Leave any field empty if you can't find the information.

Schema:
{
    "document_language": "Two-letter code of the document language",
    "title": "Title of the document",
    "document_type": "Abstract document type",
    "summary": "Two-sentence summary of the content",
    "tags": ["list", "of", "tags", "related", "to", "the", "document"],
    "date": "Date of the document (if mentioned) in YYYY-MM-DD format",
    "time": "Time of the document (if mentioned) in HH:MM:SS format"
}

Reply only with the json object.
    """

    prompt_de = """
Du bist ein Experte im Extrahieren von Titeln und kurzen Zusammenfassungen aus Dokumenten.
Die verfügbaren Informationen über das Dokument beginnen mit <document> und enden mit </document>.

<document>
Ordner: {{ folder }}
Dateiname: {{ title }}
Inhalt:
{{ content }}
</document>

Extrahiere Metadaten nach folgendem JSON Schema:

{
    "document_language": "Zwei-Buchstaben-Code der Dokumentsprache, z.B. 'de' oder 'en'",
    "title": "Titel des Dokuments",
    "document_type": "Abstrakter Dokumenttyp",
    "summary": "Sehr kurze Zusammenfassung des Inhalts",
    "tags": ["Liste", "von", "Tags", "die", "mit", "dem", "Dokument", "verwandt", "sind"],
    "date": "Datum des Dokuments (falls erwähnt) im Format JJJJ-MM-TT",
    "time": "Uhrzeit des Dokuments (falls erwähnt) im Format HH:MM:SS"
}

Erläuterungen zu den Feldern:

document_language: Der Zwei-Buchstaben-Code der Dokumentsprache, z.B. 'de' oder 'en'.

title: Der Titel des Dokuments. Wenn ein Titel im Dokument genannt wird, soll er exakt so wiedergegeben werden.
Wenn kein Titel genannt wird, soll ein möglichst treffender, kurzer Titel gewählt werden.
Der Dateiname kann als Inspiration dienen, muss aber nicht übernommen werden.

document_type: Der abstrakte Dokumenttyp. Beispiele sind: "Aufsatz über einen neuen Algorithmus", "Bericht über eine Müllverbrennungsanlage", "Präsentation über ein neues Produkt".

summary: Die Zusammenfassung sollten zwei Sätze sein, die das Wesentliche des Dokuments erfassen.
Fasse die Sätz kurz, ohne Füllwörter. Konzentriere dich auf Informationen, die wichtig sein können um das Dokument zu finden, z.B. Wer, Was, Wann, Wo, Warum.

tags: Bis zu 10 Stichwörter, die das Dokument beschreiben. Nutze sowohl allgemeine Stichworte als auch spezifische Begriffe,
die im Dokument vorkommen, zum Beispiel Orte, Personen oder Technologien. Füge alle direkt beteiligten Personen als Tags hinzu.

date: Das Datum des Dokuments, falls es im Text oder Dateinamen erwähnt wird. Gib das Datum im Format JJJJ-MM-TT an. Falls nur ein Jahr oder Monat genannt wird, nutze den 01. des entsprechenden Monats.

time: Die Uhrzeit des Dokuments, falls sie im Text erwähnt wird (zum Beispiel der Startzeitpunkt eines Meetings). Gib die Uhrzeit im Format HH:MM:SS an.

Lasse ein Feld leer, wenn du die Information nicht finden kannst.
Texte und Stichwörter sollen in deutscher Sprache sein, egal in welcher Sprache das Dokument verfasst ist.
Nutze auch den Ordnername für Hinweise aus die Bedeutung eines Dokuments.

Antworte nur mit dem JSON-Objekt. Antworte mit einem vollständigen JSON-Objekt, auch wenn du nicht alle Felder ausfüllen kannst.
    """

    prompt = (prompt_de.replace("{{ title }}", title)
              .replace("{{ folder }}", folder or "")
              .replace("{{ content }}", full_text[:1000]))
    model = BaseLLMModel.load(Google_Gemini_Flash_1_5_v1.__name__)
    response = model.generate_prompt_response(
        system_prompt=prompt,
        max_tokens=2000,
    )
    response_text = response.conversation[-1].content
    assert isinstance(response_text, str)
    try:
        info = json.loads(response_text)
    except (KeyError, ValueError):
        logging.warning(f"Failed to parse AI response: {response_text}")
        return None
    result = AiMetadataResult(**info)
    return result
