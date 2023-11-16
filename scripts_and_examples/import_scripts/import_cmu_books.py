import logging
import time
import gzip
import json
import sys
import csv

import tqdm
import orjson

from data_backend_client import update_database_layout, insert_many, files_in_folder

sys.path.append('../../data_backend/')
from utils.dotdict import DotDict


def preprocess_item(raw_item: list) -> dict:
    item = {
        "wikipedia_id": raw_item[0],
        "freebase_id": raw_item[1],
        "title": raw_item[2],
        "author": raw_item[3],
        "publication_date": raw_item[4] or None,  # making sure its None rather than empty string for OpenSearch
        "genre": raw_item[5],
        "summary": raw_item[6],
    }
    try:
        item["genre"] = list(json.loads(item["genre"]).values())
    except:
        pass
    return item


def import_dataset():
    dataset_id = 9
    update_database_layout(dataset_id)

    max_items = 1000000

    items = []
    total_items = 0

    filename = "/data/cmu_books_16k/booksummaries.txt"
    with open(filename, 'r') as f:
        for line in csv.reader(f, dialect='excel-tab'):
            item = preprocess_item(line)

            items.append(item)
            total_items += 1

            if total_items % 512 == 0:
                t1 = time.time()
                insert_many(dataset_id, items)
                t2 = time.time()
                print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(items))*1000:.2f} ms")
                items = []
            if total_items >= max_items:
                break

    if items:
        t1 = time.time()
        insert_many(dataset_id, items)
        t2 = time.time()
        print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(items))*1000:.2f} ms")


if __name__ == "__main__":
    import_dataset()
