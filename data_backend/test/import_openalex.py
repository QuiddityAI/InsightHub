"""
Run with "python3 -m test.import_openalex"
"""
import json
import time
import os
import logging
import gzip
import sys
from typing import Tuple

import orjson
import tqdm
from logic.insert_logic import insert_many, update_database_layout

# logging.root.setLevel(logging.INFO)


def files_in_folder(path, extensions:Tuple[str]=(".gz",)):
    return [os.path.join(path, name) for path, subdirs, files in os.walk(path)
            for name in files if name.lower().endswith(extensions)]


completed_files_file = "openalex_completed_files.txt"


def get_completed_files():
    if not os.path.exists(completed_files_file):
        return set()
    with open(completed_files_file, "r") as f:
        completed_files = set([x.strip() for x in f.readlines() if x.strip()])
    return completed_files


def add_filename_to_completed_file(filename):
    completed_files = get_completed_files()
    completed_files.add(filename)
    with open(completed_files_file, "w") as f:
        f.write("\n".join(list(completed_files)))


def get_item_count(filename):
    with open("/data/openalex/openalex-snapshot/data/works/manifest", "r") as f:
        manifest = json.load(f)
    filename = filename.replace("/data/openalex/openalex-snapshot", "")
    for entry in manifest["entries"]:
        if filename in entry["url"]:
            return entry["meta"]["record_count"]
    return None


def reconstruct_abstract(inverted_abstract):
    length = inverted_abstract["IndexLength"]
    placeholder = [""] * length
    for word, locs in inverted_abstract["InvertedIndex"].items():
        for l in locs:
            placeholder[l] = word
    return " ".join(placeholder)


def import_openalex():
    gz_files = sorted(files_in_folder("/data/openalex/openalex-snapshot/data/works"), reverse=False)
    completed_files = get_completed_files()
    total_elements_added = 0

    dataset_id = 6
    update_database_layout(dataset_id)

    for filename in tqdm.tqdm(gz_files):
        if filename in completed_files:
            continue
        logging.warning(f"Processing {filename}...")
        total_elements_added += import_gz_file(filename, dataset_id)
        add_filename_to_completed_file(filename)
        logging.warning(f"Total elements added: {total_elements_added}")
    return


def import_gz_file(filename, dataset_id):
    counter = 0
    max_elements = 1000000000
    elements = []

    with gzip.open(filename,'r') as f:
        for line in tqdm.tqdm(f, total=get_item_count(filename)):
            try:
                work = orjson.loads(line)  # orjson is about 0.03ms faster (30%) than json, meaning about 15% of total time per item
                if work.get("is_paratext"):
                    continue
                # if work.get("language") and work.get("language") != "en":
                #     continue
                if not work.get("abstract_inverted_index"):
                    continue
                if "article" not in work.get("type", "") and "posted-content" not in work.get("type", ""):
                    continue
                primary_location_source = work.get("primary_location", {}).get("source", {}) if work.get("primary_location", {}) else None
                item = {
                    "_id": work["id"].split("/")[-1],
                    "doi": work["doi"],
                    "type": work["type"],
                    "title": work["title"],
                    "authors": [x.get("author", {}).get("display_name", "unknown") for x in work["authorships"]],
                    "primary_location_name": primary_location_source.get("display_name", "unknown") if primary_location_source else "unknown",
                    "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
                    "publication_year": work.get("publication_year"),
                    "publication_date": work.get("publication_date"),
                    "cited_by_count": work.get("cited_by_count", 0),
                    "open_access_url": work.get("open_access", {}).get("oa_url", None),
                    "concepts": {concept["display_name"]: concept.get("score", 0.0) for concept in work.get("concepts", [])},
                    "language": work.get("language"),
                }
                elements.append(item)
                counter += 1
            except json.decoder.JSONDecodeError as e:
                logging.error(repr(e))

            if counter % min(max_elements, 2048) == 0:
                t1 = time.time()
                try:
                    insert_many(dataset_id, elements)
                except (Exception, KeyboardInterrupt) as e:
                    logging.error(e)
                    logging.warning(f"Currently processed file: {filename}, items added from this file: {counter}")
                    sys.exit()
                duration = time.time() - t1
                print(f"Duration: {duration:.3f}s, time per item: {(duration / len(elements))*1000:.2f} ms, added from this file: {counter}")
                elements = []

            if counter >= max_elements:
                break

        # process remaining items:
        if elements:
            t1 = time.time()
            try:
                insert_many(dataset_id, elements)
            except (Exception, KeyboardInterrupt) as e:
                logging.error(e)
                logging.warning(f"Currently processed file: {filename}, items added from this file: {counter}")
                sys.exit()
            duration = time.time() - t1
            print(f"Duration: {duration:.3f}s, time per item: {(duration / len(elements))*1000:.2f} ms, added from this file: {counter}")
            elements = []
    return counter


"""
Before OpenAlex:
Filesystem      Size  Used Avail Use% Mounted on
tmpfs           6,3G  2,8M  6,3G   1% /run
/dev/nvme0n1p4   55G   13G   39G  25% /
tmpfs            32G  4,0K   32G   1% /dev/shm
tmpfs           5,0M   12K  5,0M   1% /run/lock
/dev/nvme0n1p1  197M   35M  163M  18% /boot/efi
/dev/nvme0n1p3  672G  462G  176G  73% /data
/dev/nvme0n1p5  124G   26G   92G  22% /home
tmpfs           6,3G   56K  6,3G   1% /run/user/1000

After 1M:


"""

def print_few_lines_of_gz_file(filename):
    counter = 0
    with gzip.open(filename,'r') as f:
        t1 = time.time()
        for line in f:
            work = orjson.loads(line)
            if work.get("is_paratext"):
                continue
            # if work.get("language") and work.get("language") != "en":
            #     continue
            if not work.get("abstract_inverted_index"):
                continue
            if "article" not in work.get("type", "") and "posted-content" not in work.get("type", ""):
                continue
            counter += 1
            if counter % 10000 == 0:
                duration = time.time() - t1
                print(f"Duration: {duration:.3f}s, time per item: {(duration / counter)*1000:.2f} ms, added from this file: {counter}")
                print(work["id"], work["publication_date"], filename)


if __name__ == "__main__":
    import_openalex()
    #gz_files = sorted(files_in_folder("/data/openalex/openalex-snapshot/data/works"), reverse=False)
    #for f in gz_files[:410]:
    #    add_filename_to_completed_file(f)
    #print_few_lines_of_gz_file(gz_files[411])
