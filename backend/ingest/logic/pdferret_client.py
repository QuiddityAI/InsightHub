import os
import json
import logging

import requests
from llmonkey.llms import Mistral_Pixtral, Nebius_Llama_3_1_70B_fast, Google_Gemini_Flash_1_5_v1

from data_map_backend.utils import DotDict

PDFERRET_BASE_URL = os.getenv("PDFERRET_BASE_URL", "http://localhost:8000")


def extract_using_pdferret(
    file_paths: list[str],
    vision_model: str = Google_Gemini_Flash_1_5_v1.__name__,
    text_model: str = Google_Gemini_Flash_1_5_v1.__name__,
    doc_lang: str = "en",
    return_images: bool = True,
) -> tuple[list[DotDict], list[DotDict]]:
    if not PDFERRET_BASE_URL:
        raise ValueError("PDFERRET_BASE_URL environment variable is not set")
    url = f"{PDFERRET_BASE_URL}/process_files_by_stream"
    headers = {"accept": "application/json"}
    files = []
    for fpath in file_paths:
        files.append(
            ("pdfs", (os.path.basename(fpath), open(fpath, "rb"), "application/pdf"))
        )
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
    response = requests.post(url, headers=headers, files=files, data=data, timeout=max_sec_per_file*len(file_paths))

    response_json = response.json()

    if 'extracted' not in response_json:
        logging.error(f"Error in pdferret response: {response_json}")

    docs = response_json.get("extracted", [])
    errors = response_json.get("errors", [])

    docs = [DotDict(doc) for doc in docs]
    errors = [DotDict(err) for err in errors]

    return docs, errors
