from typing import Callable, Iterable
import logging
import os
import uuid

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import pypdfium2 as pdfium

from utils.dotdict import DotDict
from database_client.text_search_engine_client import TextSearchEngineClient
from database_client.django_client import get_dataset, get_import_converter
from logic.insert_logic import insert_many, update_database_layout

UPLOADED_FILES_FOLDER = "/data/quiddity_data/uploaded_files"


def upload_files(dataset_id: int, import_converter_id: int, files: Iterable[FileStorage]) -> list[tuple]:
    import_converter = get_import_converter(import_converter_id)
    logging.warning(f"uploading files to dataset {dataset_id}, import_converter: {import_converter}")
    if not os.path.exists(UPLOADED_FILES_FOLDER):
        os.makedirs(UPLOADED_FILES_FOLDER)
    paths = []
    for file in files:
        logging.warning(f"saving file: {file.filename}")
        new_uuid = str(uuid.uuid4())
        secure_name = secure_filename(file.filename or '')
        suffix = secure_name.split('.')[-1]
        filename = secure_name.replace(f".{suffix}", f"_{new_uuid}.{suffix}")
        sub_folder = f"{dataset_id}/{new_uuid[:2]}"
        if not os.path.exists(f"{UPLOADED_FILES_FOLDER}/{sub_folder}"):
            os.makedirs(f"{UPLOADED_FILES_FOLDER}/{sub_folder}")
        sub_path = f"{sub_folder}/{filename}"
        path = f"{UPLOADED_FILES_FOLDER}/{sub_path}"
        file.save(path)
        paths.append(sub_path)

    converter_func = get_import_converter_by_name(import_converter.module)
    items = converter_func(paths, import_converter.parameters)

    dataset = get_dataset(dataset_id)
    text_search_engine_client = TextSearchEngineClient()
    if text_search_engine_client.get_item_count(dataset.actual_database_name) == 0:
        logging.warning(f"Updating database layout for dataset {dataset_id} because there aren't any items in the database yet.")
        update_database_layout(dataset_id)

    inserted_ids = insert_many(dataset_id, items)
    logging.warning(f"inserted {len(items)} items to dataset {dataset_id}")
    return inserted_ids


def get_import_converter_by_name(name: str) -> Callable:
    if name == "scientific_article_pdf":
        return _scientific_article_pdf
    raise ValueError(f"import converter {name} not found")


def _scientific_article_pdf(paths, parameters):
    from pdfparser import grobid_parser # only load import here to improve startup time

    parser = grobid_parser.GROBIDParser(grobid_address='http://grobid:8070')
    parsed = parser.fit_transform({sub_path: f'{UPLOADED_FILES_FOLDER}/{sub_path}' for sub_path in paths})
    items = []
    for sub_path, parsed_pdf in parsed.items():
        parsed_pdf = DotDict(parsed_pdf)
        try:
            pub_year = int(parsed_pdf.pub_date.split("-")[0])
        except:
            pub_year = None

        full_text_original_chunks = _postprocess_pdf_chunks(parsed_pdf.sections)
        full_text = " ".join(full_text_original_chunks)

        try:
            pdf = pdfium.PdfDocument(f'{UPLOADED_FILES_FOLDER}/{sub_path}')
            first_page = pdf[0]
            image = first_page.render(scale=1).to_pil()
            thumbnail_path = f'{sub_path}.thumbnail.jpg'
            image.save(f'{UPLOADED_FILES_FOLDER}/{thumbnail_path}', 'JPEG', quality=60)
        except Exception as e:
            logging.warning(f"Failed to create thumbnail for {sub_path}: {e}")
            thumbnail_path = None

        items.append({
            "id": parsed_pdf.doi or str(uuid.uuid5(uuid.NAMESPACE_URL, sub_path)),
            "doi": parsed_pdf.doi,
            "title": parsed_pdf.title,
            "abstract": parsed_pdf.abstract,
            "authors": parsed_pdf.authors,
            "journal": "unknown",
            "publication_year": pub_year,
            "cited_by": 0,
            "file_path": sub_path,  # relative to UPLOADED_FILES_FOLDER
            "thumbnail_path": thumbnail_path,  # relative to UPLOADED_FILES_FOLDER
            "full_text": full_text,
            "full_text_original_chunks": full_text_original_chunks,
        })
    return items


def _postprocess_pdf_chunks(sections):
    max_paragraph_length = 2000  # characters
    full_text_original_chunks = []
    for section in sections:
        paragraphs = section.text  # 'section.text' is an array of texts
        if isinstance(paragraphs, str):
            paragraphs = [paragraphs]
        assert isinstance(paragraphs, list)
        if not paragraphs:
            continue
        i = 0
        while i < len(paragraphs):
            if len(paragraphs[i]) > max_paragraph_length * 1.2:
                # split long paragraphs into smaller ones
                paragraphs.insert(i + 1, paragraphs[i][max_paragraph_length:])
                paragraphs[i] = paragraphs[i][:max_paragraph_length]
            i += 1
        if len(paragraphs) >= 2:
            for i in range(len(paragraphs) - 1, 1, -1):
                if len(paragraphs[i]) < 120:
                    # if the paragraph is too short, merge it with the previous one
                    paragraphs[i - 1] = paragraphs[i - 1] + " " + paragraphs[i]
                    del paragraphs[i]
        if len(paragraphs[0]) < 80:
            if len(paragraphs) > 1:
                # if the first paragraph is too short, merge it with the second one
                paragraphs[1] = paragraphs[0] + " " + paragraphs[1]
                del paragraphs[0]
            else:
                # if there is only one paragraph and it is too short, skip the section
                continue
        if section.heading:
            paragraphs[0] = section.heading + ": " + paragraphs[0]
        full_text_original_chunks += paragraphs
    return full_text_original_chunks