from typing import Callable, Iterable
import logging
import os
import uuid

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from database_client.text_search_engine_client import TextSearchEngineClient
from database_client.django_client import get_dataset, get_import_converter
from logic.insert_logic import insert_many, update_database_layout


def upload_files(dataset_id: int, import_converter_id: int, files: Iterable[FileStorage]):
    import_converter = get_import_converter(import_converter_id)
    logging.warning(f"uploading files to dataset {dataset_id}, import_converter: {import_converter}")
    uploaded_files_folder = "/data/quiddity_data/uploaded_files"
    if not os.path.exists(uploaded_files_folder):
        os.makedirs(uploaded_files_folder)
    paths = []
    for file in files:
        logging.warning(f"saving file: {file.filename}")
        new_uuid = uuid.uuid4().hex
        filename = f"{new_uuid}_{secure_filename(file.filename or '')}"
        path = f"{uploaded_files_folder}/{filename}"
        file.save(path)
        paths.append(path)

    converter_func = get_import_converter_by_name(import_converter.module)
    items = converter_func(paths, import_converter.parameters)

    dataset = get_dataset(dataset_id)
    text_search_engine_client = TextSearchEngineClient()
    if text_search_engine_client.get_item_count(dataset.actual_database_name) == 0:
        logging.warning(f"Updating database layout for dataset {dataset_id} because there aren't any items in the database yet.")
        update_database_layout(dataset_id)

    insert_many(dataset_id, items)
    logging.warning(f"inserted {len(items)} items to dataset {dataset_id}")


def get_import_converter_by_name(name: str) -> Callable:
    if name == "scientific_article_pdf":
        return _scientific_article_pdf
    raise ValueError(f"import converter {name} not found")


def _scientific_article_pdf(paths, parameters):
    items = []
    for path in paths:
        items.append({
            "doi": uuid.uuid4().hex,
            "title": "A scientific article",
            "abstract": "This is an abstract",
            "authors": "John Doe, Jane Doe",
            "container_title": "Journal of Science",
            "publication_year": 2021,
            "cited_by": 50,
            "file_path": path,
        })
    return items