import gzip
import requests
import json
from pathlib import Path
import os
import pickle
import logging
import time
import sys

import orjson
from tqdm import tqdm

from download_semantic_scholar_dataset import DatasetNames

# add '../import_scripts/' to sys.path:
sys.path.append(str(Path(__file__).resolve().parents[1] / 'import_scripts'))
from data_backend_client import update_database_layout, insert_many

# configure logging like [timestamp] [loglevel with fixed length] message
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)-8s] %(message)s')


base_download_folder = f'/data/semantic_scholar'

tldr_file_paths = {}
tldr_index = {}
tldr_files = {}
abstract_file_paths = {}
abstract_index = {}
abstract_files = {}


def load_indexes():
    global tldr_file_paths, tldr_index, tldr_files, abstract_file_paths, abstract_index, abstract_files
    logging.warning("Loading indexes...")
    t1 = time.time()
    tldr_file_paths, tldr_index = pickle.load(open(Path(base_download_folder) / f"tldrs.index.pkl", 'rb'))
    abstract_file_paths, abstract_index = pickle.load(open(Path(base_download_folder) / f"abstracts.index.pkl", 'rb'))
    duration = time.time() - t1
    logging.warning(f"Indexes loaded in {duration:.2f} seconds")


def get_tldr(corpusid):
    t1 = time.time()
    file_id, pos, length = tldr_index.get(corpusid, (None, None, None))
    if file_id is None:
        return None
    file_path = tldr_file_paths[file_id]
    if file_path not in tldr_files:
        #logging.info(f"Opening file {file_path}")
        tldr_files[file_path] = open(file_path, 'rb')
    file = tldr_files[file_path]
    file.seek(pos)
    line = file.readline()
    data = orjson.loads(line)
    duration_ms = (time.time() - t1) * 1000
    #logging.info(f"get_tldr took {duration_ms:.2f} ms")  # about 0.16ms on average
    return data


def get_abstract(corpusid):
    t1 = time.time()
    file_id, pos, length = abstract_index.get(corpusid, (None, None, None))
    if file_id is None:
        return None
    file_path = abstract_file_paths[file_id]
    if file_path not in abstract_files:
        #logging.info(f"Opening file {file_path}")
        abstract_files[file_path] = open(file_path, 'rb')
    file = abstract_files[file_path]
    file.seek(pos)
    line = file.readline()
    data = orjson.loads(line)
    duration_ms = (time.time() - t1) * 1000
    #logging.info(f"get_abstract took {duration_ms:.2f} ms")  # about 0.16ms on average
    return data


progress_file = Path(base_download_folder) / "import_progress.pkl"
def add_processed_file(file_name):
    files = get_processed_files()
    files.append(file_name)
    with open(progress_file, 'wb') as f:
        pickle.dump(files, f)


def get_processed_files():
    if progress_file.exists():
        with open(progress_file, 'rb') as f:
            return pickle.load(f)
    return []



def import_papers(dataset_id):
    dataset_name = DatasetNames.PAPERS
    dataset_folder = Path(base_download_folder) / dataset_name
    total_items = 0
    processed_files = get_processed_files()
    for i, file_name in enumerate(os.listdir(dataset_folder)):
        if file_name in processed_files:
            logging.info(f"Skipping file {i+1} of {len(os.listdir(dataset_folder))}: {file_name}")
            continue
        logging.info(f"Importing file {i+1} of {len(os.listdir(dataset_folder))}: {file_name}")
        file_path = dataset_folder / file_name
        try:
            total_items += import_file(file_path, dataset_id, i)
            add_processed_file(file_name)
        except KeyboardInterrupt:
            logging.warning("Interrupted")
            break
    logging.warning(f"Imported {total_items} items")



UNIQUE_BUT_COMMON_WORDS = [
    { 'lang': 'en', 'words': [" the ", " this ", " and ", " be "] },
    { 'lang': 'de', 'words': [" der ", " und ", " für ", " über ", " aber ", " ein ", " eine ", " einer ", " zur ", " aus ", " von "] },
    { 'lang': 'fr', 'words': [" le ", " un ", " avec ", " dans ", " mais ", " aprés "] },
    { 'lang': 'es', 'words': [" el ", " ser ", " esto ", " muy ", " ahora "] },
    { 'lang': 'pt', 'words': [" com ", " não "] },
    { 'lang': 'zh', 'words': ["的", "是", "了", "不"] },
    { 'lang': 'ru', 'words': [" и ", " в ", " на ", " что "] },
    { 'lang': 'ja', 'words': ["の", "は", "に", "を"] },
    { 'lang': 'it', 'words': [" una ", " con ", " ma "] },
    { 'lang': 'tr', 'words': [" ve ", " bir ", " için ", " ile ", " gibi ", " ama ", " veya "] },
    { 'lang': 'nl', 'words': [" het ", " een ", " maar "] },
    { 'lang': 'sv', 'words': [" och ", " att ", " ett " ] },
    { 'lang': 'in', 'words': [" dan ", " ini ", " itu ", " yang "] },
]
LESS_UNIQUE_ENGLISH_WORDS = [" of ", " for ", " is ", " which ", " here ", " where ", " review ", " studies ", " study ", " research ", " results ", " analysis ", " method ", " methods ", " approach ", " approaches ", " solution ", " solutions "]


def guess_language(title, abstract, tldr):
    if abstract and len(abstract) > 50:
        for lang in UNIQUE_BUT_COMMON_WORDS:
            if any(common_word in abstract for common_word in lang['words']):
                return lang['lang']
        # if no common words found, try with lower case:
        for lang in UNIQUE_BUT_COMMON_WORDS:
            if any(common_word in abstract.lower() for common_word in lang['words']):
                return lang['lang']
    elif tldr and len(tldr) > 50:
        # tldr is always English for now:
        return 'en'
    for lang in UNIQUE_BUT_COMMON_WORDS:
        if any(common_word in title.lower() for common_word in lang['words']):
            return lang['lang']
    # if no unique words were found, try some common English words:
    if any(common_word in title.lower() for common_word in LESS_UNIQUE_ENGLISH_WORDS):
        return 'en'
    return None


def import_file(file_path, dataset_id, index):
    max_items = None
    item_count = 0
    item_batch = []
    batch_size = 256
    with gzip.open(file_path, 'rt', encoding='utf-8') as gz:
        batch_time_start = time.time()
        for line in gz:
            t1 = time.time()
            try:
                data = orjson.loads(line)
            except Exception as e:
                print(e)
                print(line)
                continue
            if not data.get('title') or not data.get('corpusid'):
                continue
            #print(json.dumps(data, indent=2))
            corpusid = data['corpusid']
            tldr = get_tldr(corpusid)
            tldr_text = tldr.get('text') if tldr else None
            abstract = get_abstract(corpusid)
            abstract_text = abstract.get('abstract') if abstract else None
            language = guess_language(data['title'], abstract_text, tldr_text)
            item = {
                'corpus_id': str(corpusid),
                'title': data['title'],
                'abstract': abstract_text or tldr_text,
                'tldr': tldr_text,
                'authors': [e['name'] for e in data.get('authors', [])],
                'author_ids': [e['authorId'] for e in data.get('authors', [])],
                'doi': data.get('externalids', {}).get('DOI'),
                'venue': data.get('venue'),
                'publication_year': data.get('year'),
                'publication_date': data.get('publicationdate'),
                'cited_by': data.get('citationcount'),
                'influential_citation_count': data.get('influentialcitationcount'),
                'is_open_access': data.get('isopenaccess'),
                'publication_types': data.get('publicationtypes'),
                'journal': (data.get('journal') or {}).get('name'),
                'journal_info': data.get('journal') or {},
                'language': language,
                #'full_text': None, # imported separately
            }
            #print(json.dumps(tldr, indent=2))
            #print(json.dumps(abstract, indent=2))
            #duration_ms = (time.time() - t1) * 1000
            #logging.info(f"combining item took {duration_ms:.2f} ms")  # about 0.3ms is there are abstracts

            item_count += 1

            item_batch.append(item)
            if len(item_batch) >= batch_size:
                #t2 = time.time()
                #duration_converting_per_item = (t2 - batch_time_start) * 1000 / len(item_batch)
                #logging.info(f"converting a batch took {duration_converting_per_item:.2f} ms per item")
                insert_many(dataset_id, item_batch)
                #duration_ms = ((time.time() - t2) * 1000) / batch_size
                #logging.info(f"importing a batch took {duration_ms:.2f} ms per item")
                if item_count % (batch_size * 400) == 0:
                    duration_total_per_item = (time.time() - batch_time_start) * 1000 / len(item_batch)
                    total_items = 200000000
                    estimated_total_time_hours = ((duration_total_per_item / 1000) * total_items) / 60 / 60
                    logging.warning(f"File {index + 1}, {item_count} imported, estimated total time: {estimated_total_time_hours:.2f} hours")
                item_batch = []
                batch_time_start = time.time()


            if max_items and item_count >= max_items:
                break

        # ingest last partial batch:
        if item_batch:
            t2 = time.time()
            insert_many(dataset_id, item_batch)
            duration_ms = ((time.time() - t2) * 1000) / len(item_batch)
            logging.info(f"importing a batch took {duration_ms:.2f} ms per item")
    return item_count


if __name__ == "__main__":
    dataset_id = 80
    #update_database_layout(dataset_id)
    load_indexes()
    import_papers(dataset_id)
    logging.warning("Done")
