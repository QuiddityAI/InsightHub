from typing import Callable, Iterable, Optional
import logging
import os
import uuid
import threading
import datetime

from legacy_backend.utils.field_types import FieldType
from legacy_backend.database_client.text_search_engine_client import TextSearchEngineClient
from legacy_backend.database_client.django_client import get_dataset, get_import_converter, add_item_to_collection, get_service_usage, track_service_usage
from legacy_backend.logic.insert_logic import insert_many, update_database_layout
from legacy_backend.logic.local_map_cache import clear_local_map_cache
from ingest.schemas import UploadedOrExtractedFile, CustomUploadedFile, UploadedFileMetadata
from ingest.logic.office_documents import import_office_document
from ingest.logic.scientific_articles import scientific_article_pdf, scientific_article_csv, scientific_article_form
from ingest.logic.generic_import_formats import import_csv, import_website_url
from ingest.logic.common import UPLOADED_FILES_FOLDER
from ingest.logic.store_on_disk import store_uploaded_file, unpack_archive

upload_tasks = {}


def upload_files_or_forms(dataset_id: int, import_converter: str, raw_files: Optional[Iterable[CustomUploadedFile]],
                 forms: Optional[list[dict]],
                 collection_id: int | None, collection_class: str | None,
                 user_id: int, blocking: bool=False, skip_generators: bool=False) -> str:
    """ Import files: extracting text -> converting to items -> inserting into database """
    global upload_tasks
    task_id = _create_upload_task(dataset_id)

    def run():
        try:
            if raw_files:
                inserted_ids, failed_files = _store_files_and_import_them(dataset_id, import_converter, raw_files,
                    collection_id, collection_class, task_id, user_id, skip_generators)
            else:
                assert forms
                # import JSON objects from a form -> no file upload etc, but still converting first
                inserted_ids, failed_files = _import_items(dataset_id, import_converter, forms,
                    collection_id, collection_class, task_id, user_id, skip_generators=skip_generators)
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
            for file in raw_files or []:
                file.uploaded_file.close()

    thread = threading.Thread(target=run)
    thread.start()
    if blocking:
        thread.join()
    return task_id


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


def get_upload_task_status(dataset_id: int) -> list[dict]:
    return list(upload_tasks.get(dataset_id, {}).values())


def get_upload_task_status_by_id(dataset_id: int, task_id: str) -> dict:
    return upload_tasks.get(dataset_id, {}).get(task_id, {})


def _set_task_status(dataset_id: int, task_id: str, status: str, progress: float):
    upload_tasks[dataset_id][task_id]["status"] = status
    upload_tasks[dataset_id][task_id]["progress"] = progress


def _store_files_and_import_them(dataset_id: int, import_converter_identifier: str, raw_files: Iterable[CustomUploadedFile],
                 collection_id: int | None, collection_class: str | None, task_id: str,
                 user_id: int, skip_generators: bool = False) -> tuple[list[tuple], list[str]]:
    logging.warning(f"uploading files to dataset {dataset_id}, import_converter: {import_converter_identifier}")
    if not os.path.exists(UPLOADED_FILES_FOLDER):
        os.makedirs(UPLOADED_FILES_FOLDER)
    _set_task_status(dataset_id, task_id, "storing files", 0.0)

    # check if user is allowed to upload this many files before storing them
    # to prevent filling up the disk with files that can't be imported
    service_usage = get_service_usage(user_id, "upload_items")
    remaining_allowed_items = service_usage["limit_per_period"] - service_usage["usage_current_period"]
    raw_files = list(raw_files)
    if len(raw_files) > remaining_allowed_items:
        raise ValueError(f"Too many files, limit is {remaining_allowed_items}")

    uploaded_files: list[UploadedOrExtractedFile] = []
    failed_files = []
    for i, custom_file in enumerate(raw_files):
        file = custom_file.uploaded_file
        if not file.name: continue
        if file.name.endswith(".tar.gz") or file.name.endswith(".zip"):
            new_paths, new_failed_files = unpack_archive(file, dataset_id, user_id)
            uploaded_files += new_paths
            failed_files += new_failed_files
            continue
        # logging.warning(f"saving file: {file.name}")
        try:
            sub_path, md5 = store_uploaded_file(file, dataset_id)
            uploaded_files.append(
                UploadedOrExtractedFile(
                    local_path=sub_path,
                    original_filename=file.name,
                    metadata=UploadedFileMetadata(
                        folder=custom_file.metadata.folder if custom_file.metadata else None,
                        created_at=custom_file.metadata.created_at if custom_file.metadata else None,
                        size_in_bytes=custom_file.metadata.size_in_bytes if custom_file.metadata else None,
                        mime_type=custom_file.metadata.mime_type if custom_file.metadata else None,
                        md5_hex=md5
                    )
                ))
        except Exception as e:
            logging.warning(f"failed to save file: {e}")
            # print traceback
            import traceback
            traceback.print_exc()
            failed_files.append({"filename": file.name, "reason": str(e)})
        _set_task_status(dataset_id, task_id, "storing files", i / len(raw_files))  # type: ignore

    if not uploaded_files:
        return [], failed_files

    return _import_items(dataset_id, import_converter_identifier, uploaded_files,
                         collection_id, collection_class, task_id, user_id, failed_files, skip_generators)


def _import_items(dataset_id: int, import_converter_identifier: str, files_or_dicts: list,
                 collection_id: int | None, collection_class: str | None, task_id: str,
                 user_id: int, failed_files: list = [], skip_generators: bool = False) -> tuple[list[tuple], list[str]]:
    response = track_service_usage(user_id, "upload_items", len(files_or_dicts), "uploading items")
    if not response["approved"]:
        raise ValueError("service usage not approved")

    import_converter = get_import_converter(import_converter_identifier)
    converter_func = get_import_converter_by_name(import_converter.module)
    items, failed_ids = converter_func(files_or_dicts, import_converter.parameters, lambda progress: _set_task_status(dataset_id, task_id, "converting files", progress))
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
        inserted_ids += insert_many(dataset_id, items[i:i + batch_size], skip_generators=skip_generators)
    logging.warning(f"inserted {len(items)} items to dataset {dataset_id}")
    clear_local_map_cache()

    if collection_id is not None and collection_class is not None:
        _set_task_status(dataset_id, task_id, "adding to collection", 0.0)
        for i, ds_and_item_id in enumerate(inserted_ids):
            _set_task_status(dataset_id, task_id, "adding to collection", i / len(inserted_ids))
            ds_id, item_id = ds_and_item_id
            add_item_to_collection(collection_id, collection_class, True, FieldType.IDENTIFIER, None, ds_id, item_id, 1.0)

    return inserted_ids, failed_files


def get_import_converter_by_name(code_module_name: str) -> Callable:
    if code_module_name == "scientific_article_pdf":
        return scientific_article_pdf
    elif code_module_name == "scientific_article_csv":
        return scientific_article_csv
    elif code_module_name == "scientific_article_form":
        return scientific_article_form
    elif code_module_name == "csv":
        return import_csv
    elif code_module_name == "website_url":
        return import_website_url
    elif code_module_name == "office_document":
        return import_office_document
    raise ValueError(f"import converter {code_module_name} not found")
