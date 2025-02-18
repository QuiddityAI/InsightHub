import csv
import gzip
import json
import logging
import sys
import time

import orjson
import tqdm

from data_backend_client import files_in_folder, insert_many, update_database_layout

sys.path.append("../../data_backend/")
from utils.dotdict import DotDict


def import_dataset():
    dataset_id = 12
    update_database_layout(dataset_id)

    max_items = 1000000

    items = []
    total_items = 0

    for filename in files_in_folder("/data/unsplash_25k", extensions=(".jpg",)):
        item = {
            "image_id": filename.split("/")[-1].split(".")[0],
            "image": filename,
        }

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
