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


def to_float(text: str):
    try:
        return float(text)
    except:
        return None


def to_int(text: str):
    try:
        return int(text)
    except:
        return None


def preprocess_item(raw_item: list, companies: dict) -> dict:
    item = {
        "job_id": raw_item[0],
        "title": raw_item[2],
        "description": raw_item[3],
        "salary": {
            "max": to_float(raw_item[4]),
            "med": to_float(raw_item[5]),
            "min": to_float(raw_item[6]),
        },
        "work_type": raw_item[8],
        "location": raw_item[9],
        "applies": raw_item[10],
        "remote_allowed": raw_item[12] == "1",
        "views": raw_item[13],
        "job_posting_url": raw_item[14],
        "skill_description": raw_item[20],
        "company_name": companies.get(raw_item[1], {}).get("name"),
        "company_description": companies.get(raw_item[1], {}).get("description"),
        "company_employee_count": companies.get(raw_item[1], {}).get("employee_count"),
        "company_follower_count": companies.get(raw_item[1], {}).get("follower_count"),
    }
    if raw_item[7] == "MONTHLY":
        item["salary"]["max"] = item["salary"]["max"] * 12 if isinstance(item["salary"]["max"], (int, float)) else None
        item["salary"]["med"] = item["salary"]["med"] * 12 if isinstance(item["salary"]["med"], (int, float)) else None
        item["salary"]["min"] = item["salary"]["min"] * 12 if isinstance(item["salary"]["min"], (int, float)) else None
    elif raw_item[7] == "HOURLY":
        item["salary"]["max"] = (
            item["salary"]["max"] * 40 * 52 if isinstance(item["salary"]["max"], (int, float)) else None
        )
        item["salary"]["med"] = (
            item["salary"]["med"] * 40 * 52 if isinstance(item["salary"]["med"], (int, float)) else None
        )
        item["salary"]["min"] = (
            item["salary"]["min"] * 40 * 52 if isinstance(item["salary"]["min"], (int, float)) else None
        )
    return item


employee_counts = {}
filename = "/data/linkedin_jobs_2023_33k/employee_counts.csv"
with open(filename, "r") as f:
    f.__next__()  # skip header
    for line in csv.reader(f):
        employee_counts[line[0]] = {
            "employee_count": to_int(line[1]),
            "follower_count": to_int(line[2]),
        }

companies = {}
filename = "/data/linkedin_jobs_2023_33k/companies.csv"
with open(filename, "r") as f:
    f.__next__()  # skip header
    for line in csv.reader(f):
        companies[line[0]] = {
            "company_id": line[0],
            "name": line[1],
            "description": line[2],
        }
        companies[line[0]].update(employee_counts.get(line[0], {}))


def import_companies():
    dataset_id = 11
    update_database_layout(dataset_id)

    max_items = 1000000

    items = []
    total_items = 0

    for company in companies.values():
        items.append(company)
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
    print("Companies completed")


def import_dataset():
    dataset_id = 10
    update_database_layout(dataset_id)

    max_items = 1000000

    items = []
    total_items = 0

    filename = "/data/linkedin_jobs_2023_33k/job_postings.csv"
    with open(filename, "r") as f:
        f.__next__()  # skip header
        for line in csv.reader(f):
            if len(line) < 21:
                continue
            item = preprocess_item(line, companies)

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
    import_companies()
    import_dataset()
