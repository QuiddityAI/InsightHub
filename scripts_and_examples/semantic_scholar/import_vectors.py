"""
Note: the backend container port needs to be exposed for this script to work,
it does not work by going through the backend proxy for now.
"""


import gzip
import requests
import json
from pathlib import Path
import os
import pickle
import logging
import time
import sys
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from threading import Thread

import orjson
from tqdm import tqdm

from download_semantic_scholar_dataset import (
    DatasetNames,
    get_dataset_file_urls,
    streaming_download,
    download_gz_file_using_curl,
)

# add '../import_scripts/' to sys.path:
sys.path.append(str(Path(__file__).resolve().parents[1] / "import_scripts"))
from data_backend_client import update_database_layout, insert_many, insert_vectors

# configure logging like [timestamp] [loglevel with fixed length] message
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)-8s] %(message)s")


base_download_folder = f"/data/semantic_scholar"


progress_file = Path(base_download_folder) / "vector_import_progress.pkl"


def add_processed_file(file_name):
    files = get_processed_files()
    files.append(file_name)
    with open(progress_file, "wb") as f:
        pickle.dump(files, f)


def get_processed_files():
    if progress_file.exists():
        with open(progress_file, "rb") as f:
            return pickle.load(f)
    return []


total_items = 0


def import_vectors(dataset_id, release):
    dataset_name = DatasetNames.SPECTER_V2
    processed_files = get_processed_files()
    files = sorted(get_dataset_file_urls(release, dataset_name))
    thread_future = None
    pool = ThreadPoolExecutor(max_workers=1)
    download_folder = Path(base_download_folder) / DatasetNames.SPECTER_V2
    download_folder.mkdir(parents=True, exist_ok=True)

    def handle_file(i, link):
        nonlocal thread_future
        file_name = link.split("/")[-1].split("?")[0]
        file_name = file_name.replace(".gz", "")
        file_path = download_folder / file_name
        if file_path in processed_files:
            logging.info(f"Skipping file {i+1} of {len(files)}: {file_path}")
            return 0
        logging.info(f"Importing file {i+1} of {len(files)}: {file_path}")
        if not file_path.exists():
            download_gz_file_using_curl(link, file_path, uncompress=True)
        if thread_future:
            # usually, the import is faster than the download, but in case its not, wait for the last import to finish
            thread_future.result()  # wait for the last import to finish and raise an exception if it failed
        thread_future = pool.submit(import_vector_file, file_path, dataset_id)

    for i, link in enumerate(files):
        handle_file(i, link)
    if thread_future:
        # usually, the import is faster than the download, but in case its not, wait for the last import to finish
        thread_future.result()  # wait for the last import to finish and raise an exception if it failed
    logging.warning(f"Done importing all {total_items} items")
    return True


def import_vector_file(file_path, dataset_id):
    global total_items
    batch_pks = []
    batch_vectors = []
    batch_size = 512
    threads = 8
    batches = []
    batch_start = time.time()
    item_count = 0
    excluded_filter_fields = []
    thread_pool = ThreadPoolExecutor(max_workers=threads)
    est_total_items = 200000000

    with open(file_path, "rb") as f:
        for line in f:
            element = orjson.loads(line)
            vector = orjson.loads(element["vector"])
            # print(json.dumps(vector[0], indent=2))
            batch_pks.append(str(element["corpusid"]))
            batch_vectors.append(vector)

            if len(batch_pks) >= batch_size:
                batches.append((batch_pks, batch_vectors))
                batch_pks = []
                batch_vectors = []

            if len(batches) >= threads:
                items_to_be_inserted = sum([len(batch[0]) for batch in batches])
                duration_ms_per_item_preprocessing = (time.time() - batch_start) / items_to_be_inserted * 1000
                # preprocessing is fast, 90% is spent in fetching the text data and inserting the vectors in Qdrant
                processing_start = time.time()
                futures = [
                    thread_pool.submit(
                        lambda batch: insert_vectors(
                            dataset_id, "embedding_specter_v2", batch[0], batch[1], excluded_filter_fields
                        ),
                        batch,
                    )
                    for batch in batches
                ]
                completed, not_completed = wait(futures, timeout=None, return_when=ALL_COMPLETED)
                # check if any future had an exception:
                for future in completed:
                    if future.exception():
                        logging.error(f"Exception in thread: {future.exception()}")
                        raise future.exception()
                item_count += items_to_be_inserted
                duration_ms_per_item_proc = (time.time() - processing_start) / items_to_be_inserted * 1000
                duration_ms_per_item = (time.time() - batch_start) / items_to_be_inserted * 1000
                estimated_time_hours = est_total_items * (duration_ms_per_item / 1000) / 60 / 60
                if item_count % (batch_size * threads) == 0:
                    logging.info(
                        f"{item_count} items, {duration_ms_per_item_preprocessing:.2f} ms preprocessing, {duration_ms_per_item_proc:.3f} ms proc, {duration_ms_per_item:.2f} ms per item, estimated time: {estimated_time_hours:.2f} hours"
                    )
                    pass
                batch_start = time.time()
                batches = []

        if batch_pks:
            insert_vectors(dataset_id, "embedding_specter_v2", batch_pks, batch_vectors, excluded_filter_fields)
            duration_ms_per_item = (time.time() - batch_start) / len(batch_pks) * 1000
            estimated_time_hours = est_total_items * (duration_ms_per_item / 1000) / 60 / 60
            logging.info(
                f"{item_count} items, {duration_ms_per_item:.2f} ms per item, estimated time: {estimated_time_hours:.2f} hours"
            )
            batch_start = time.time()
            item_count += len(batch_pks)
            batch_pks = []
            batch_vectors = []

    os.remove(file_path)
    total_items += item_count
    add_processed_file(file_path)
    logging.warning(f"Imported {total_items} items")


if __name__ == "__main__":
    dataset_id = 80
    release = "2024-06-18"
    retries = 5
    success = False
    while not success and retries > 0:
        try:
            success = import_vectors(dataset_id, release)
            break
        except KeyboardInterrupt:
            logging.warning("Interrupted")
            break
        except Exception as e:
            logging.error(f"Failed to import vectors: {e}")
            retries -= 1
            logging.warning(f"Retrying in 120 seconds")
            time.sleep(120)
            logging.warning(f"Retrying now")
    logging.warning("Done")
