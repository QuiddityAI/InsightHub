import gzip
import requests
import json
from pathlib import Path
import os

import orjson
from tqdm import tqdm

def load_env_file():
    with open("../../.env", "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.strip().split("=")
            os.environ[key] = value

load_env_file()

API_KEY = os.getenv('SEMANTIC_SCHOLAR_API_KEY')

class DatasetNames():
    PAPERS = 'papers'
    AUTHORS = 'authors'
    ABSTRACTS = 'abstracts'
    S2ORC = 's2orc'
    TLDRS = 'tldrs'
    SPECTER_V2 = 'embeddings-specter_v2'


def print_releases():
    releases = requests.get('https://api.semanticscholar.org/datasets/v1/release').json()
    print(releases[-3:])
    # ['2023-08-29', '2023-09-05', '2023-09-12']


def print_release_info(release):
    r2 = requests.get(f'https://api.semanticscholar.org/datasets/v1/release/{release}').json()
    print(json.dumps(r2, indent=2))


def get_dataset_file_urls(release, dataset_name):
    headers = {
        "x-api-key": API_KEY,
    }
    result = requests.get(f'https://api.semanticscholar.org/datasets/v1/release/{release}/dataset/{dataset_name}', headers=headers).json()  # type: ignore
    # print(json.dumps(result, indent=2))
    # # {
    # #   "name": "abstracts",
    # #   "description": "Paper abstract text, where available. 100M records in 30 1.8GB files.",
    # #   "README": "Semantic Scholar Academic Graph Datasets The "abstracts" dataset provides...",
    # #   "files": [
    # #     "https://ai2-s2ag.s3.amazonaws.com/dev/staging/2023-03-28/abstracts/20230331_0..."
    # #   ]
    # # }
    files = result['files']
    return files


def download_gz_file_using_curl(file_url, file_path, uncompress=True):
    # use curl and uncompress using gz:
    if uncompress:
        cmd = f'curl -L "{file_url}" | gzip -d > "{file_path}"'
    else:
        cmd = f'curl -L -o "{file_path}" "{file_url}"'
    print(f"Downloading to {file_path}...")
    try:
        code = os.system(cmd)
    except KeyboardInterrupt as e:
        os.remove(file_path)
        raise e
    if code != 0:
        print(f"Error downloading {file_path}")
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
        raise Exception(f"Error downloading {file_path}")


def streaming_download(link):
    # not used for now, its slower than downloading a file and at the same time process the last file
    headers = {
        "x-api-key": API_KEY,
    }
    import logging
    with requests.get(link, headers=headers, stream=True) as response:  # type: ignore
        response.raise_for_status()
        with gzip.open(response.raw, 'rt', encoding='utf-8') as gz:
            for line in gz:
                try:
                    data = orjson.loads(line)
                    yield data
                except Exception as e:
                    print(e)
                    print(line)
                    continue


def s3_url_to_filename(s3_url):
    return s3_url.split('/')[-1].split('?')[0]


def inspect_paper_file(file_path):
    max_items = 1
    item_count = 0
    with gzip.open(file_path, 'rt', encoding='utf-8') as gz:
        for line in gz:
            try:
                data = orjson.loads(line)
            except Exception as e:
                print(e)
                print(line)
                continue
            if not data['publicationdate']:
                continue
            print(json.dumps(data, indent=2))
            item_count += 1
            if item_count >= max_items:
                break


def inspect_s2orc_file(file_path):
    max_items = 1
    item_count = 0
    with gzip.open(file_path, 'rt', encoding='utf-8') as gz:
        for line in gz:
            try:
                data = orjson.loads(line)
            except Exception as e:
                print(e)
                print(line)
                continue
            print(json.dumps(data, indent=2))
            item_count += 1
            if item_count >= max_items:
                break


def test_papers():
    release = '2024-06-18'
    base_download_folder = f'/data/semantic_scholar'
    dataset_name = DatasetNames.PAPERS
    dataset_folder = Path(base_download_folder) / dataset_name

    file_urls = get_dataset_file_urls(release, dataset_name)
    max_files = 0

    for file_url in file_urls[:max_files]:
        file_name = s3_url_to_filename(file_url)
        os.makedirs(dataset_folder, exist_ok=True)
        file_path = dataset_folder / file_name
        print(f'Downloading {file_name}...')
        #download_file_using_curl(file_url, file_path)

    for file_name in os.listdir(dataset_folder):
        print(f'Inspecting {file_name}...')
        file_path = dataset_folder / file_name
        inspect_paper_file(file_path)


def download_files(dataset_name, uncompress=False):
    release = '2024-06-18'
    base_download_folder = f'/data/semantic_scholar'
    dataset_folder = Path(base_download_folder) / dataset_name

    file_urls = get_dataset_file_urls(release, dataset_name)
    max_files = 5000

    for i, file_url in enumerate(file_urls[:max_files]):
        file_name = s3_url_to_filename(file_url)
        if uncompress:
            file_name = file_name.replace('.gz', '')
        os.makedirs(dataset_folder, exist_ok=True)
        file_path = dataset_folder / file_name
        if os.path.exists(file_path):
            continue
        print(f'Downloading {i + 1} of {len(file_urls[:max_files])}: {file_name}...')
        download_gz_file_using_curl(file_url, file_path, uncompress=uncompress)

    print("Done")


def test_s2orc():
    release = '2024-06-18'
    base_download_folder = f'/data/semantic_scholar'
    dataset_name = DatasetNames.S2ORC
    dataset_folder = Path(base_download_folder) / dataset_name

    file_urls = get_dataset_file_urls(release, dataset_name)
    max_files = 1

    for file_url in file_urls[:max_files]:
        file_name = s3_url_to_filename(file_url)
        os.makedirs(dataset_folder, exist_ok=True)
        file_path = dataset_folder / file_name
        print(f'Downloading {file_name}...')
        download_gz_file_using_curl(file_url, file_path)

    for file_name in os.listdir(dataset_folder):
        print(f'Inspecting {file_name}...')
        file_path = dataset_folder / file_name
        inspect_s2orc_file(file_path)


if __name__ == '__main__':
    # test_papers()
    # test_s2orc()
    download_files(DatasetNames.TLDRS, uncompress=True)
    download_files(DatasetNames.ABSTRACTS, uncompress=True)
    #download_files(DatasetNames.S2ORC)
    download_files(DatasetNames.PAPERS)


