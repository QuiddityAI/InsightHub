import os
import logging
from typing import Tuple
import json
import datetime

import requests
import cbor2


data_backend_url = os.getenv("backend_host", "http://127.0.0.1:55125")


def update_database_layout(dataset_id: int):
    url = data_backend_url + "/data_backend/update_database_layout"
    data = {"dataset_id": dataset_id}
    response = requests.post(url, json=data)
    if response.status_code != 204:
        logging.error(f"Error during update_database_layout: {repr(response)}, {response.text}")
        raise Exception(response)
    else:
        logging.info(f"Updated database layout of database {dataset_id}")


def insert_many(dataset_id: int, elements: list[dict], skip_generators: bool = False):
    url = data_backend_url + "/data_backend/insert_many_sync"
    data = {
        "dataset_id": dataset_id,
        "elements": elements,
        "skip_generators": skip_generators,
    }
    response = requests.post(url, json=data)
    if response.status_code != 204:
        logging.error(f"Error during insert_many_sync: {repr(response)}, {response.text}")
        raise Exception(response)


def insert_vectors(
    dataset_id: int,
    vector_field: str,
    item_pks: list[str],
    vectors: list[list[float]],
    excluded_filter_fields: list[str] = [],
):
    url = data_backend_url + "/data_backend/insert_vectors_sync"
    data = {
        "dataset_id": dataset_id,
        "vector_field": vector_field,
        "item_pks": item_pks,
        "vectors": vectors,
        "excluded_filter_fields": excluded_filter_fields,
    }
    cbor_data = cbor2.dumps(data)
    response = requests.post(url, data=cbor_data)
    if response.status_code != 204:
        logging.error(f"Error during insert_vectors_sync: {repr(response)}, {response.text}")
        raise Exception(response)


def upload_files(
    dataset_id: int,
    schema_identifier: str,
    user_id: int,
    organization_id: int,
    import_converter: str,
    collection_id: str | None = None,
    collection_class: str | None = None,
    file_paths: list[str] = [],
    exclude_prefix: str | None = None,
    skip_generators: bool = False,
):
    url = data_backend_url + "/api/v1/ingest/upload_files"
    data = {
        "dataset_id": dataset_id,
        "schema_identifier": schema_identifier,
        "user_id": user_id,
        "organization_id": organization_id,
        "import_converter": import_converter,
        "collection_id": collection_id,
        "collection_class": collection_class,
        "dataset_auth_token": "fixme",  # TODO: use proper auth token
        "blocking": True,
        "skip_generators": skip_generators,
    }
    files = {}
    for i, file_path in enumerate(file_paths):
        files[f"file_{i}"] = open(file_path, "rb")
        sub_path = file_path.replace(exclude_prefix, "") if exclude_prefix else file_path
        data[f"file_{i}_metadata"] = json.dumps(
            {
                "folder": os.path.dirname(sub_path),
                "created_at": datetime.datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                "updated_at": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                "size_in_bytes": os.path.getsize(file_path),
                "mime_type": None,
                "md5_hex": None,
            }
        )
    response = requests.post(url, data=data, files=files)
    if response.status_code != 200:
        logging.error(f"Error during upload_files: {repr(response)}, {response.text}")
        raise Exception(response)
    return response.json()


def check_pk_existence(dataset_id: int, pks: list[str], access_token: str):
    url = data_backend_url + "/api/v1/ingest/check_pk_existence"
    data = {
        "dataset_id": dataset_id,
        "pks": pks,
        "access_token": access_token,
    }
    response = requests.post(url, json=data)
    if response.status_code != 200:
        logging.error(f"Error during check_pk_existence: {repr(response)}, {response.text}")
        raise Exception(response)
    return response.json()


def files_in_folder(path, extensions: Tuple[str, ...] = (".gz",)):
    return sorted(
        [
            os.path.join(path, name)
            for path, subdirs, files in os.walk(path)
            for name in files
            if name.lower().endswith(extensions)
        ]
    )
