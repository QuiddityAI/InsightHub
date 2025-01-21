import logging
import sys
import time

import tqdm
import orjson

from data_backend_client import update_database_layout, insert_many


def get_publish_year(value):
    if isinstance(value, str):
        value = value.split(" ")[-1]
    try:
        value = int(value)
        return value if (value > 0 and value < 2040) else None
    except (ValueError, TypeError):
        return None


def get_first_cover(lst):
    if lst:
        return str(lst[0])
    return None


def get_author_names(author_list, authors: dict):
    if not author_list:
        return []
    name = lambda a: a.get("key") if isinstance(a, dict) else a
    return [authors.get(name(x.get("author", {}))) for x in author_list]


def preprocess_item(raw_item: dict, authors: dict) -> dict:
    cover_id = get_first_cover(raw_item.get("covers"))
    description = raw_item.get("description", None)
    if isinstance(description, dict):
        description = description.get("value")
    item = {
        "work_id": raw_item["key"],  # correct
        "title": raw_item.get("title"),  # correct
        #'translated_titles': [x.get('text') for x in raw_item.get('translated_titles', [])],  # only exists for 5 books
        "subtitle": raw_item.get("subtitle"),  # correct
        "authors": get_author_names(raw_item.get("authors"), authors),  # correct
        "subjects": set(raw_item.get("subjects") or []),  # correct
        "description": description,  # correct
        "first_publish_year": get_publish_year(raw_item.get("first_publish_date")),  # correct
        # 'first_publish_date': None,  # exact date not in works
        "cover": cover_id,  # correct
        "cover_thumbnail": f"https://covers.openlibrary.org/b/id/{cover_id}-S.jpg" if cover_id else None,  # correct
        #'languages': [x.get('key') for x in raw_item.get('original_languages', [])],  # only exists for 5 books
        #'genres': [],  # not in works, don't store empty set because it uses a lot of memory
        #'series': [],  # not in works
        "number_of_pages": None,  # not in works
        #'isbn_13': [],  # not in works
        #'publishers': [],  # not in works
    }
    if "subject_places" in raw_item:
        item["subject_places"] = raw_item.get("subject_places")
    if "subject_times" in raw_item:
        item["subject_times"] = raw_item.get("subject_times")
    if "subject_people" in raw_item:
        item["subject_people"] = raw_item.get("subject_people")
    return item


editions_without_work = 0
work_not_found = 0


def process_edition(raw_item: dict, works: dict):
    global editions_without_work, work_not_found
    if not "works" in raw_item:
        editions_without_work += 1
        return
    edition_works = raw_item.get("works", [])
    if not edition_works:
        print(f"Work not specified for edition {raw_item}")
        return
    work_id = edition_works[0].get("key")
    if work_id not in works:
        work_not_found += 1
        # print(f"Work {work_id} not found")
        # print(type(work_id))
        # print(len(works))
        return
    work = works[work_id]
    subtitle = raw_item.get("subtitle")
    if subtitle and not work["subtitle"]:
        work["subtitle"] = subtitle
    work["subjects"] |= set(raw_item.get("subjects") or [])
    languages = [x["key"].replace("/languages/", "") for x in raw_item.get("languages", []) if "key" in x]
    description = raw_item.get("description", None)
    if isinstance(description, dict):
        description = description.get("value")
    if description:
        english_and_longer = "eng" in languages and len(description) > len(work["description"])
        if not work["description"] or english_and_longer:
            work["description"] = description
            work["languages"] = languages
            if subtitle:
                work["subtitle"] = subtitle
    if languages and "languages" not in work:
        work["languages"] = languages
    publish_year = get_publish_year(raw_item.get("publish_date"))
    if publish_year and (not work["first_publish_year"] or publish_year < work["first_publish_year"]):
        work["first_publish_year"] = publish_year
    cover_id = get_first_cover(raw_item.get("covers", []))
    if cover_id and not work["cover"]:
        work["cover"] = cover_id
        work["cover_thumbnail"] = f"https://covers.openlibrary.org/b/id/{cover_id}-S.jpg"
    genres = raw_item.get("genres")
    if genres:
        if "genres" in work:
            work["genres"] = list(set(genres) | set(work["genres"]))
        else:
            work["genres"] = genres
    series = raw_item.get("series")
    if series:
        if "series" in work:
            work["series"] = list(set(series) | set(work["series"]))
        else:
            work["series"] = series
    pages = get_publish_year(raw_item.get("number_of_pages"))
    work["number_of_pages"] = (
        max(work["number_of_pages"], pages) if work["number_of_pages"] and pages else pages or work["number_of_pages"]
    )
    isbn_13 = raw_item.get("isbn_13")
    if isbn_13:
        if isinstance(isbn_13[0], dict):
            isbn_13 = [x.get("value") for x in isbn_13]
        if "isbn_13" in work:
            work["isbn_13"] = list(set(isbn_13) | set(work["isbn_13"]))
        else:
            work["isbn_13"] = isbn_13
    publishers = raw_item.get("publishers")
    if publishers:
        if isinstance(publishers[0], dict):
            publishers = [x.get("name") for x in publishers]
        if "publishers" in work:
            work["publishers"] = list(set(publishers) | set(work["publishers"]))
        else:
            work["publishers"] = publishers


def import_dataset():
    dataset_id = 25
    update_database_layout(dataset_id)

    authors = {}
    with open("/data/openlibrary_20M/ol_dump_authors_latest.txt", "r") as f:
        for row in tqdm.tqdm(f, total=12645831):
            type_, author_id, revision, last_modified, json_raw = row.split("\t")
            raw_item = orjson.loads(json_raw)
            if "name" not in raw_item:
                continue
            authors[raw_item["key"]] = raw_item["name"]

    # run garbage collection
    import gc

    print("Collecting garbage")
    gc.collect()
    print("Done gc")

    works = {}
    with open("/data/openlibrary_20M/ol_dump_works_latest.txt", "r") as f:
        for row in tqdm.tqdm(f, total=33638099):
            type_, work_id, revision, last_modified, json_raw = row.split("\t")
            raw_item = orjson.loads(json_raw)
            item = preprocess_item(raw_item, authors)
            # print(json.dumps(item, indent=2, ensure_ascii=False))
            works[item["work_id"]] = item
            if len(works) % 10000000 == 0:
                print("Collecting garbage")
                gc.collect()
                print("Done gc")

    print("Collecting garbage")
    gc.collect()
    print("Done gc")

    i = 0
    with open("/data/openlibrary_20M/ol_dump_editions_latest.txt", "r") as f:
        for row in tqdm.tqdm(f, total=47336172):
            type_, edition_id, revision, last_modified, json_raw = row.split("\t")
            raw_item = orjson.loads(json_raw)
            try:
                process_edition(raw_item, works)
            except Exception as e:
                # exc_tb = sys.exc_info()[2]
                # print(f"Failed to process edition {edition_id}: {e} {exc_tb.tb_lineno}")  # type: ignore
                raise e
            # print(json.dumps(item, indent=2, ensure_ascii=False))
            i += 1
            if i % 10000000 == 0:
                print("Collecting garbage")
                gc.collect()
                print("Done gc")

    items = []
    total_items = 0
    for item in works.values():
        if "subjects" in item:
            item["subjects"] = list(item["subjects"])

        items.append(item)
        total_items += 1

        if total_items % 512 == 0:
            t1 = time.time()
            insert_many(dataset_id, items)
            t2 = time.time()
            print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(items))*1000:.2f} ms")
            print(f"Estimated remaining time: {(len(works) - total_items) * ((t2 - t1)/len(items)) / 60:.2f} min")
            items = []
    if items:
        t1 = time.time()
        insert_many(dataset_id, items)
        t2 = time.time()
        print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(items))*1000:.2f} ms")

    print(f"Editions without Work ('orphans'): {editions_without_work}")
    print(f"Work not found: {work_not_found}")
    print("Done")


if __name__ == "__main__":
    import_dataset()
