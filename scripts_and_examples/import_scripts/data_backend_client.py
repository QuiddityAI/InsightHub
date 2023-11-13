import os
import logging

import requests


data_backend_url = os.getenv("data_backend_host", "http://localhost:55123")


def update_database_layout(dataset_id: int):
    url = data_backend_url + '/data_backend/update_database_layout'
    data = {'dataset_id': dataset_id}
    response = requests.post(url, json=data)
    if response.status_code != 204:
        logging.error(f"Error during update_database_layout: {repr(response)}, {response.text}")
        raise Exception(response)
    else:
        logging.info(f"Updated database layout of database {dataset_id}")


def insert_many(dataset_id: int, elements: list[dict]):
    url = data_backend_url + '/data_backend/insert_many_sync'
    data = {
        'dataset_id': dataset_id,
        'elements': elements,
    }
    response = requests.post(url, json=data)
    if response.status_code != 204:
        logging.error(f"Error during insert_many_sync: {repr(response)}, {response.text}")
        raise Exception(response)
