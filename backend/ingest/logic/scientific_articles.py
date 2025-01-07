import logging
import csv
import uuid
from dataclasses import asdict

import pypdfium2 as pdfium

from data_map_backend.utils import pk_to_uuid_id
from ingest.schemas import UploadedOrExtractedFile
from ingest.logic.common import UPLOADED_FILES_FOLDER


def scientific_article_pdf(paths: list[UploadedOrExtractedFile], parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
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
            "id": pdf_metainfo.doi or pk_to_uuid_id(uploaded_file.local_path),
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


def scientific_article_csv(paths: list[UploadedOrExtractedFile], parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    for uploaded_file in paths:
        csv_reader = csv.DictReader(open(f'{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}', 'r'))
        for i, row in enumerate(csv_reader):
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            try:
                items.append({
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
                })
            except Exception as e:
                logging.warning(f"Failed to parse row {i} in {uploaded_file.local_path}: {e}")
        if on_progress:
            on_progress(0.5 + (len(items) / len(paths)) * 0.5)

    return items, []


def scientific_article_form(raw_items, parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
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
