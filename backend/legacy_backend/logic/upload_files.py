from copy import deepcopy
from typing import Callable, Iterable
import logging
import os
import uuid
import tarfile
import zipfile
import hashlib
import threading
import datetime
import csv
import json
import subprocess
from dataclasses import asdict

from ninja import Schema
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import pypdfium2 as pdfium
import requests

from django.core.files import File

from ..utils.field_types import FieldType
from ..database_client.text_search_engine_client import TextSearchEngineClient
from ..database_client.django_client import get_dataset, get_import_converter, add_item_to_collection, get_service_usage, track_service_usage
from ..logic.insert_logic import insert_many, update_database_layout
from ..logic.local_map_cache import clear_local_map_cache
from data_map_backend.groq_client import GROQ_MODELS, get_groq_response_using_history

UPLOADED_FILES_FOLDER = "/data/quiddity_data/uploaded_files"


upload_tasks = {}

# only applies to single files, not archives
# (this is also why it can't be enforced by flask's max_content_length)
MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def _create_upload_task(dataset_id: int):
    global upload_tasks
    # delete any finished tasks from upload_tasks[dataset_id]:
    if dataset_id not in upload_tasks:
        upload_tasks[dataset_id] = {}
    for task_id in list(upload_tasks[dataset_id].keys()):
        if not upload_tasks[dataset_id][task_id]["is_running"]:
            del upload_tasks[dataset_id][task_id]

    task_id = str(uuid.uuid4())
    upload_tasks[dataset_id][task_id] = {
        "task_id": task_id,
        "started_at": datetime.datetime.now().isoformat(),
        "finished_at": None,
        "is_running": True,
        "status": "started",
        "progress": 0.0,
        "inserted_ids": [],
        "failed_files": [],
    }
    return task_id


def upload_files(dataset_id: int, import_converter: str, files: Iterable[File],
                 collection_id: int | None, collection_class: str | None,
                 user_id: int) -> str:
    global upload_tasks
    task_id = _create_upload_task(dataset_id)

    def run():
        try:
            inserted_ids, failed_files = _store_files_and_import_them(dataset_id, import_converter, files,
                 collection_id, collection_class, task_id, user_id)
            upload_tasks[dataset_id][task_id]["is_running"] = False
            upload_tasks[dataset_id][task_id]["status"] = "finished"
            upload_tasks[dataset_id][task_id]["finished_at"] = datetime.datetime.now().isoformat()
            upload_tasks[dataset_id][task_id]["progress"] = 1.0
            upload_tasks[dataset_id][task_id]["inserted_ids"] = inserted_ids
            upload_tasks[dataset_id][task_id]["failed_files"] = failed_files
        except Exception as e:
            logging.warning(f"upload_files failed: {e}")
            # print traceback
            import traceback
            traceback.print_exc()
            upload_tasks[dataset_id][task_id]["is_running"] = False
            upload_tasks[dataset_id][task_id]["status"] = f"failed ({str(e)})"
            upload_tasks[dataset_id][task_id]["finished_at"] = datetime.datetime.now().isoformat()
        finally:
            for file in files:
                file.close()

    thread = threading.Thread(target=run)
    thread.start()
    return task_id


def import_items(dataset_id, import_converter, items, collection_id, collection_class, user_id: int):
    global upload_tasks
    task_id = _create_upload_task(dataset_id)

    def run():
        try:
            inserted_ids, failed_files = _import_items(dataset_id, import_converter, items,
                 collection_id, collection_class, task_id, user_id)
            upload_tasks[dataset_id][task_id]["is_running"] = False
            upload_tasks[dataset_id][task_id]["status"] = "finished"
            upload_tasks[dataset_id][task_id]["finished_at"] = datetime.datetime.now().isoformat()
            upload_tasks[dataset_id][task_id]["progress"] = 1.0
            upload_tasks[dataset_id][task_id]["inserted_ids"] = inserted_ids
            upload_tasks[dataset_id][task_id]["failed_files"] = failed_files
        except Exception as e:
            logging.warning(f"upload_files failed: {e}")
            # print traceback
            import traceback
            traceback.print_exc()
            upload_tasks[dataset_id][task_id]["is_running"] = False
            upload_tasks[dataset_id][task_id]["status"] = f"failed ({str(e)})"
            upload_tasks[dataset_id][task_id]["finished_at"] = datetime.datetime.now().isoformat()

    thread = threading.Thread(target=run)
    thread.start()
    return task_id


def get_upload_task_status(dataset_id: int) -> list[dict]:
    return list(upload_tasks.get(dataset_id, {}).values())


def _set_task_status(dataset_id: int, task_id: str, status: str, progress: float):
    upload_tasks[dataset_id][task_id]["status"] = status
    upload_tasks[dataset_id][task_id]["progress"] = progress


class UploadedFile(Schema):
    local_path: str
    original_filename: str


def _store_files_and_import_them(dataset_id: int, import_converter_identifier: str, files: Iterable[File],
                 collection_id: int | None, collection_class: str | None, task_id: str,
                 user_id: int) -> tuple[list[tuple], list[str]]:
    logging.warning(f"uploading files to dataset {dataset_id}, import_converter: {import_converter_identifier}")
    if not os.path.exists(UPLOADED_FILES_FOLDER):
        os.makedirs(UPLOADED_FILES_FOLDER)
    _set_task_status(dataset_id, task_id, "storing files", 0.0)

    # check if user is allowed to upload this many files before storing them
    # to prevent filling up the disk with files that can't be imported
    service_usage = get_service_usage(user_id, "upload_items")
    remaining_allowed_items = service_usage["limit_per_period"] - service_usage["usage_current_period"]
    files = list(files)
    if len(files) > remaining_allowed_items:
        raise ValueError(f"Too many files, limit is {remaining_allowed_items}")

    paths: list[UploadedFile] = []
    failed_files = []
    for i, file in enumerate(files):
        if not file.name: continue
        if file.name.endswith(".tar.gz") or file.name.endswith(".zip"):
            new_paths, new_failed_files = _unpack_archive(file, dataset_id, user_id)
            paths += new_paths
            failed_files += new_failed_files
            continue
        logging.warning(f"saving file: {file.name}")
        try:
            sub_path = _store_uploaded_file(file, dataset_id)
            paths.append(UploadedFile(local_path=sub_path, original_filename=file.name))
        except Exception as e:
            logging.warning(f"failed to save file: {e}")
            # print traceback
            import traceback
            traceback.print_exc()
            failed_files.append({"filename": file.name, "reason": str(e)})
        _set_task_status(dataset_id, task_id, "storing files", i / len(files))  # type: ignore

    if not paths:
        return [], failed_files

    return _import_items(dataset_id, import_converter_identifier, paths,
                         collection_id, collection_class, task_id, user_id, failed_files)


def _import_items(dataset_id: int, import_converter_identifier: str, paths_or_items: list,
                 collection_id: int | None, collection_class: str | None, task_id: str,
                 user_id: int, failed_files: list = []) -> tuple[list[tuple], list[str]]:
    response = track_service_usage(user_id, "upload_items", len(paths_or_items), "uploading items")
    if not response["approved"]:
        raise ValueError("service usage not approved")

    import_converter = get_import_converter(import_converter_identifier)
    converter_func = get_import_converter_by_name(import_converter.module)
    items, failed_ids = converter_func(paths_or_items, import_converter.parameters, lambda progress: _set_task_status(dataset_id, task_id, "converting files", progress))
    failed_files += failed_ids

    _set_task_status(dataset_id, task_id, "inserting into DB", 0.0)
    dataset = get_dataset(dataset_id)
    text_search_engine_client = TextSearchEngineClient()
    if text_search_engine_client.get_item_count(dataset) == 0:
        logging.warning(f"Updating database layout for dataset {dataset_id} because there aren't any items in the database yet.")
        update_database_layout(dataset_id)

    _set_task_status(dataset_id, task_id, "inserting into DB", 0.1)
    batch_size = 128
    inserted_ids = []
    for i in range(0, len(items), batch_size):
        _set_task_status(dataset_id, task_id, "inserting into DB", 0.1 + i / len(items) * 0.9)
        inserted_ids += insert_many(dataset_id, items[i:i + batch_size])
    logging.warning(f"inserted {len(items)} items to dataset {dataset_id}")
    clear_local_map_cache()

    if collection_id is not None and collection_class is not None:
        _set_task_status(dataset_id, task_id, "adding to collection", 0.0)
        for i, ds_and_item_id in enumerate(inserted_ids):
            _set_task_status(dataset_id, task_id, "adding to collection", i / len(inserted_ids))
            ds_id, item_id = ds_and_item_id
            add_item_to_collection(collection_id, collection_class, True, FieldType.IDENTIFIER, None, ds_id, item_id, 1.0)

    return inserted_ids, failed_files


def _store_uploaded_file(file: File, dataset_id: int):
    temp_path = f"{UPLOADED_FILES_FOLDER}/temp_{uuid.uuid4()}"

    with open(temp_path, 'wb') as f:
        f.write(file.read())
    # check if file size is within limits, otherwise delete it to prevent filling up the disk
    # (file size can't be determined earlier as it might be a stream)
    file_size = os.path.getsize(temp_path)
    if file_size > MAX_SINGLE_FILE_SIZE:
        os.remove(temp_path)
        raise ValueError(f"File size of {file_size / 1024 / 1024:.2f} MB exceeds the limit of {MAX_SINGLE_FILE_SIZE / 1024 / 1024:.2f} MB")
    sub_path = _move_to_path_containing_md5(temp_path, file.name or '', dataset_id)
    return sub_path


def _unpack_archive(file: File, dataset_id: int, user_id: int) -> tuple[list[UploadedFile], list[str]]:
    assert file.name
    failed_files = []
    paths: list[UploadedFile] = []
    logging.warning(f"extracting archive file: {file.name}")
    is_tar = file.name.endswith(".tar.gz")
    tempfile = f"{UPLOADED_FILES_FOLDER}/temp_{uuid.uuid4()}" + (".tar.gz" if is_tar else f".zip")
    with open(tempfile, 'wb') as f:
        f.write(file.read())

    service_usage = get_service_usage(user_id, "upload_items")
    remaining_allowed_items = service_usage["limit_per_period"] - service_usage["usage_current_period"]

    try:
        if is_tar:
            archive = tarfile.open(tempfile, 'r:gz')
            members = archive.getmembers()
        else:
            archive = zipfile.ZipFile(tempfile)
            members = archive.infolist()
        logging.warning(f"contains {len(members)} files")

        # check if user is allowed to upload this many files before storing them
        # to prevent filling up the disk with files that can't be imported
        if len(members) > remaining_allowed_items:
            raise ValueError(f"Too many files in archive, limit is {remaining_allowed_items}")

        for member in members:
            file_size = member.size if isinstance(member, tarfile.TarInfo) else member.file_size
            # check if file size is within limits before extracting
            if file_size > MAX_SINGLE_FILE_SIZE:
                raise ValueError(f"File size of {file_size / 1024 / 1024:.2f} MB exceeds the limit of {MAX_SINGLE_FILE_SIZE / 1024 / 1024:.2f} MB")
            filename = member.name if isinstance(member, tarfile.TarInfo) else member.filename
            logging.warning(f"extracting file: {filename}")
            try:
                sub_path = _store_compressed_file(archive, member, dataset_id)
            except Exception as e:
                logging.warning(f"failed to extract file: {e}")
                failed_files.append({"filename": filename, "reason": str(e)})
                sub_path = None
            if sub_path:
                paths.append(UploadedFile(local_path=sub_path, original_filename=filename))
    except Exception as e:
        logging.warning(f"failed to extract archive file: {e}")
        # print stacktrace
        import traceback
        traceback.print_exc()
        failed_files.append({"filename": file.name, "reason": str(e)})
    finally:
        os.remove(tempfile)
    return paths, failed_files


def _store_compressed_file(archive: tarfile.TarFile | zipfile.ZipFile, member: tarfile.TarInfo | zipfile.ZipInfo, dataset_id: int) -> str | None:
    if isinstance(member, tarfile.TarInfo) and not member.isfile():
        return None
    if isinstance(member, zipfile.ZipInfo) and member.is_dir():
        return None
    filename = member.name if isinstance(member, tarfile.TarInfo) else member.filename
    if "MACOSX_" in filename or "_MACOSX" in filename:
        return None
    if isinstance(archive, tarfile.TarFile) and isinstance(member, tarfile.TarInfo):
        file = archive.extractfile(member)
    else:
        assert isinstance(archive, zipfile.ZipFile) and isinstance(member, zipfile.ZipInfo)
        file = archive.open(member)
    if file is None:
        logging.warning(f"failed to extract file: {filename}")
        raise ValueError("failed to extract file")
    temp_path = f"{UPLOADED_FILES_FOLDER}/temp_{uuid.uuid4()}"
    with file:
        with open(temp_path, 'wb') as f:
            f.write(file.read())
    sub_path = _move_to_path_containing_md5(temp_path, filename, dataset_id)
    return sub_path


def _move_to_path_containing_md5(temp_path: str, filename: str, dataset_id: int):
    md5 = hashlib.md5(open(temp_path,'rb').read()).hexdigest()
    secure_name = secure_filename(filename)
    suffix = secure_name.split('.')[-1]
    filename = secure_name[:-(len(suffix) + 1)] + f"_{md5}.{suffix}"
    sub_folder = f"{dataset_id}/{md5[:2]}"
    if not os.path.exists(f"{UPLOADED_FILES_FOLDER}/{sub_folder}"):
        os.makedirs(f"{UPLOADED_FILES_FOLDER}/{sub_folder}")
    sub_path = f"{sub_folder}/{filename}"
    path = f"{UPLOADED_FILES_FOLDER}/{sub_path}"
    os.rename(temp_path, path)
    return sub_path


def get_import_converter_by_name(code_module_name: str) -> Callable:
    if code_module_name == "scientific_article_pdf":
        return _scientific_article_pdf
    elif code_module_name == "scientific_article_csv":
        return _scientific_article_csv
    elif code_module_name == "scientific_article_form":
        return _scientific_article_form
    elif code_module_name == "csv":
        return _import_csv
    elif code_module_name == "website_url":
        return _import_website_url
    elif code_module_name == "office_document":
        return _import_office_document
    raise ValueError(f"import converter {code_module_name} not found")


def _scientific_article_pdf(paths: list[UploadedFile], parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    from pdferret import PDFerret
    import nltk
    nltk.download('punkt')

    extractor = PDFerret(text_extractor="grobid")
    if on_progress:
        on_progress(0.1)
    parsed, failed = extractor.extract_batch([f'{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}' for uploaded_file in paths])
    if on_progress:
        on_progress(0.5)
    failed_files = [{"filename": pdferror.file, "reason": pdferror.exc} for pdferror in failed]
    items = []
    for parsed_pdf, uploaded_file in zip(parsed, paths):
        pdf_metainfo = parsed_pdf.metainfo
        if not pdf_metainfo.title and not len(parsed_pdf.chunks):
            failed_files.append({"filename": uploaded_file.original_filename, "reason": "no title or text found, skipping"})
            continue
        # if not pdf_metainfo.title:
            # failed_files.append({"filename": sub_path, "reason": "no title found, still adding to database"})
            # add anyway because the rest of the data might be useful
        try:
            pub_year = int(pdf_metainfo.pub_date.split("-")[0])
        except:
            pub_year = None

        #full_text_original_chunks = _postprocess_pdf_chunks(parsed_pdf.chunks, parsed_pdf.title.strip())
        full_text_original_chunks = [asdict(chunk) for chunk in parsed_pdf.chunks]
        full_text = " ".join([chunk['text'] for chunk in full_text_original_chunks])

        try:
            pdf = pdfium.PdfDocument(f'{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}')
            first_page = pdf[0]
            image = first_page.render(scale=1).to_pil()
            thumbnail_path = f'{uploaded_file.local_path}.thumbnail.jpg'
            image.save(f'{UPLOADED_FILES_FOLDER}/{thumbnail_path}', 'JPEG', quality=60)
        except Exception as e:
            logging.warning(f"Failed to create thumbnail for {uploaded_file.local_path}: {e}")
            thumbnail_path = None

        items.append({
            "id": pdf_metainfo.doi or str(uuid.uuid5(uuid.NAMESPACE_URL, uploaded_file.local_path)),
            "doi": pdf_metainfo.doi,
            "title": pdf_metainfo.title.strip() or uploaded_file.original_filename,
            "abstract": pdf_metainfo.abstract,
            "authors": pdf_metainfo.authors,
            "journal": "",
            "publication_year": pub_year,
            "cited_by": 0,
            "file_path": uploaded_file.local_path,  # relative to UPLOADED_FILES_FOLDER
            "thumbnail_path": thumbnail_path,  # relative to UPLOADED_FILES_FOLDER
            "full_text": full_text,
            "full_text_original_chunks": full_text_original_chunks,
        })
        if on_progress:
            on_progress(0.5 + (len(items) / len(paths)) * 0.5)
    return items, failed_files


def _safe_to_int(s: str | None) -> int | None:
    if s is None:
        return None
    try:
        return int(s)
    except:
        return None


def _scientific_article_csv(paths: list[UploadedFile], parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    for uploaded_file in paths:
        csv_reader = csv.DictReader(open(f'{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}', 'r'))
        for i, row in enumerate(csv_reader):
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            try:
                items.append({
                    "id": row.get("doi") or str(uuid.uuid5(uuid.NAMESPACE_URL, uploaded_file.local_path + str(i))),
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
                })
            except Exception as e:
                logging.warning(f"Failed to parse row {i} in {uploaded_file.local_path}: {e}")
        if on_progress:
            on_progress(0.5 + (len(items) / len(paths)) * 0.5)

    return items, []


def _scientific_article_form(raw_items, parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    for row in raw_items:
        try:
            items.append({
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
            })
        except Exception as e:
            logging.warning(f"Failed to parse item: {e}")
        if on_progress:
            on_progress(0.5 + (len(items) / len(raw_items)) * 0.5)

    return items, []


def _import_csv(paths: list[UploadedFile], parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    if '__all__' not in parameters.get("fields", []):
        # TODO: implement custom field set
        raise ValueError("custom field set not yet implemented for csv import")

    for uploaded_file in paths:
        csv_reader = csv.DictReader(open(f'{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}', 'r'))
        for i, row in enumerate(csv_reader):
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            items.append(row)
        if on_progress:
            on_progress(0.5 + (len(items) / len(paths)) * 0.5)

    return items, []


def _import_website_url(raw_items, parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    for raw_item in raw_items:
        url = raw_item.get("url")
        # get title from url using web scraping
        headers = {'headers':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}
        result = requests.get(url, headers=headers)
        html = result.text
        title = html[html.find('<title>') + 7 : html.find('</title>')]
        items.append({
            "url": url,
            "title": title,
            "content": html,
        })

        if on_progress:
            on_progress(0.5 + (len(items) / len(raw_items)) * 0.5)

    return items, []


def _import_office_document(paths: list[UploadedFile], parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    from pdferret import PDFerret

    extractor = PDFerret(meta_extractor="dummy", text_extractor="unstructured")
    if on_progress:
        on_progress(0.1)
    parsed, failed = extractor.extract_batch([f'{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}' for uploaded_file in paths])
    failed_files = [{"filename": pdferror.file, "reason": pdferror.exc} for pdferror in failed]

    if on_progress:
        on_progress(0.5)

    items = []
    for parsed_file, uploaded_file in zip(parsed, paths):
        sub_path = uploaded_file.local_path
        file_metainfo = parsed_file.metainfo

        info_dict = file_metainfo.__dict__
        info_dict.pop('file_features')
        # -> empty for now

        if not file_metainfo.title and not len(parsed_file.chunks):
            failed_files.append({"filename": sub_path, "reason": "no title or text found, skipping"})
            continue

        full_text_chunks = [asdict(chunk) for chunk in parsed_file.chunks]
        for chunk in full_text_chunks:
            chunk.pop('chunk_type')
        full_text = " ".join([chunk['text'] for chunk in full_text_chunks])

        ai_title, ai_document_type, ai_abstract = get_ai_summary(file_metainfo.title.strip() or uploaded_file.original_filename, full_text)

        items.append({
            "title": ai_title or file_metainfo.title.strip() or uploaded_file.original_filename,
            "type_description": ai_document_type,
            "abstract": ai_abstract or file_metainfo.abstract,
            "created_at": None,
            "file_type": sub_path.split(".")[-1],
            "language": "de",  # TODO: detect language
            "uploaded_file_path": sub_path,  # relative to UPLOADED_FILES_FOLDER
            "thumbnail_path": get_thumbnail_office(sub_path),  # relative to UPLOADED_FILES_FOLDER
            "full_text": full_text,
            "full_text_chunks": full_text_chunks,
            "file_name": uploaded_file.original_filename,
            "path": "example/path/to/the/document",  # TODO: should be original path from file system
            "full_path": sub_path,  # TODO: should be original path from file system
        })
        if on_progress:
            on_progress(0.5 + (len(items) / len(paths)) * 0.5)
    return items, failed_files


def get_ai_summary(title: str, full_text: str) -> tuple[str, str, str]:
    prompt = """
You are an expert in extracting titles and short summaries from documents.
The available information about the document start with <document> and end with </document>.

<document>
Title: {{ title }}
Content: {{ content }}
</document>

Try to extract the title, the abstract document type and a one-sentence summary of the content as a JSON object.
The abstract document type should be something like: "paper about a new algorithm", "report about a waste plant", "presentation about a new product".
The summary should be a single sentence that captures the essence of the document.
Leave any field empty if you can't find the information.

Schema:
{
    "title": "Title of the document",
    "document_type": "Abstract document type",
    "summary": "One-sentence summary of the content"
}

Reply only with the json object.
    """

    prompt_de = """
Du bist ein Experte im Extrahieren von Titeln und kurzen Zusammenfassungen aus Dokumenten.
Die verfügbaren Informationen über das Dokument beginnen mit <document> und enden mit </document>.

<document>
Titel: {{ title }}
Inhalt: {{ content }}
</document>

Versuche, den Titel, den abstrakten Dokumenttyp und eine Ein-Satz-Zusammenfassung des Inhalts als JSON-Objekt zu extrahieren.
Der abstrakte Dokumenttyp sollte etwas sein wie: "Aufsatz über einen neuen Algorithmus", "Bericht über eine Müllverbrennungsanlage", "Präsentation über ein neues Produkt".
Die Zusammenfassung sollte ein einzelner Satz sein, der das Wesentliche des Dokuments erfasst.
Lasse ein Feld leer, wenn du die Information nicht finden kannst.

Schema:
{
"title": "Titel des Dokuments",
"document_type": "Abstrakter Dokumenttyp",
"summary": "Ein-Satz-Zusammenfassung des Inhalts"
}

Antworte nur mit dem JSON-Objekt.
    """

    prompt = prompt_de.replace("{{ title }}", title).replace("{{ content }}", full_text[:1000])

    history = [ { "role": "system", "content": prompt } ]
    response_text = get_groq_response_using_history(history, GROQ_MODELS.LLAMA_3_70B)  # type: ignore
    assert response_text
    try:
        info = json.loads(response_text)
    except (KeyError, ValueError):
        logging.warning(f"Failed to parse AI response: {response_text}")
        return "", "", ""
    return info.get("title", ""), info.get("document_type", ""), info.get("summary", "")


def get_thumbnail_office(sub_path) -> str | None:
    suffix = sub_path.split('.')[-1]
    file_path = f'{UPLOADED_FILES_FOLDER}/{sub_path}'
    folder = os.path.dirname(file_path)

    try:
        subprocess.run([
            'libreoffice', '--headless',
            '--convert-to','pdf:writer_pdf_Export:{"PageRange":{"type":"string","value":"1"}}',
            '--outdir', folder, file_path
            ], check=True)
        pdf_path = file_path.replace(suffix, 'pdf')
    except Exception as e:
        logging.warning(f"Failed to convert office document to pdf: {e}")
        return None

    try:
        pdf = pdfium.PdfDocument(pdf_path)
        first_page = pdf[0]
        image = first_page.render(scale=1).to_pil()
        thumbnail_path = f'{sub_path}.thumbnail.jpg'
        image.save(f'{UPLOADED_FILES_FOLDER}/{thumbnail_path}', 'JPEG', quality=60)
    except Exception as e:
        logging.warning(f"Failed to create thumbnail for {sub_path}: {e}")
        thumbnail_path = None
    return thumbnail_path
