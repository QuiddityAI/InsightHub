import json
import logging
import os
from enum import Enum
from typing import List, Tuple, TypeAlias

import requests

from config.llm import default_pdferret_models
from data_map_backend.utils import DotDict

PDFERRET_BASE_URL = os.getenv("PDFERRET_BASE_URL", "http://localhost:8000")


PDFFile: TypeAlias = str


class ChunkType(str, Enum):
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"
    OTHER = "other"


class PDFError:
    exc: str = ""
    traceback: str | list[str] = ""
    file: str = ""


class PDFChunk:
    page: int | None = None
    coordinates: List[Tuple[float, float]] | None = None
    section: str | None = None
    prefix: str | None = None
    text: str | None = None
    suffix: str | None = None
    locked: bool | None = None
    chunk_type: ChunkType | None = ChunkType.TEXT


class FileFeatures:
    filename: str = ""
    file: PDFFile | None = None
    is_scanned: bool | None = None


class MetaInfo:
    doi: str = ""
    title: str = ""
    document_type: str = ""
    search_description: str = ""
    abstract: str = ""
    authors: List[str]
    pub_date: str = ""
    mentioned_date: str = ""
    language: str = ""
    detected_language: str = ""
    file_features: FileFeatures = FileFeatures()
    npages: int = -1
    thumbnail: bytes | str = ""
    extra_metainfo: dict
    ai_metadata: str = ""


class PDFDoc:
    metainfo: MetaInfo
    chunks: List[PDFChunk]


class PDFerretResults:
    extracted: List[PDFDoc]
    errors: List[PDFError]


def extract_using_pdferret(
    file_paths: list[str],
    vision_model: str = default_pdferret_models.vision,
    text_model: str = default_pdferret_models.text,
    doc_lang: str = "en",
    return_images: bool = True,
) -> tuple[list[DotDict], list[DotDict]]:
    if not PDFERRET_BASE_URL:
        raise ValueError("PDFERRET_BASE_URL environment variable is not set")
    url = f"{PDFERRET_BASE_URL}/process_files_by_stream"
    headers = {"accept": "application/json"}
    files = []
    for fpath in file_paths:
        files.append(("pdfs", (os.path.basename(fpath), open(fpath, "rb"), "application/pdf")))
    params = {
        "vision_model": vision_model,
        "text_model": text_model,
        "lang": doc_lang,
        "return_images": return_images,
        "perfile_settings": {
            # "filename": { "lang": "de", "extra_metainfo": { "doi": "10.1234/5678" } }
        },
    }
    data = {"params": json.dumps(params)}

    # Send the POST request
    max_sec_per_file = 45
    response = requests.post(url, headers=headers, files=files, data=data, timeout=max_sec_per_file * len(file_paths))

    response_json = response.json()

    if "extracted" not in response_json:
        logging.error(f"Error in pdferret response: {response_json}")

    docs = response_json.get("extracted", [])
    errors = response_json.get("errors", [])

    docs = [DotDict(doc) for doc in docs]
    errors = [DotDict(err) for err in errors]

    return docs, errors
