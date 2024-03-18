from typing import Callable, Iterable
import logging
import os
import uuid

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from utils.dotdict import DotDict
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
    from pdfparser import grobid_parser # only load import here to improve startup time

    parser = grobid_parser.GROBIDParser(grobid_address='http://grobid:8070')
    parsed = parser.fit_transform({path: path for path in paths})
    items = []
    for path, parsed_pdf in parsed.items():
        parsed_pdf = DotDict(parsed_pdf)
        try:
            pub_year = int(parsed_pdf.pub_date.split("-")[0])
        except:
            pub_year = None
        items.append({
            "doi": parsed_pdf.doi or uuid.uuid4().hex,
            "title": parsed_pdf.title,
            "abstract": parsed_pdf.abstract,
            "authors": parsed_pdf.authors,
            "container_title": "unknown",
            "publication_year": pub_year,
            "cited_by": 0,
            "file_path": path,
        })
    return items