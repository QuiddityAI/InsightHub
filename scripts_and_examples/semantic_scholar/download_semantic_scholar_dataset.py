import gzip
import requests
import json
from pathlib import Path
import os

import orjson

def load_env_file():
    with open("../.env", "r") as f:
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


def print_releases():
    releases = requests.get('https://api.semanticscholar.org/datasets/v1/release').json()
    print(releases[-3:])
    # ['2023-08-29', '2023-09-05', '2023-09-12']


def print_release_info(release):
    r2 = requests.get(f'https://api.semanticscholar.org/datasets/v1/release/{release}').json()
    print(json.dumps(r2, indent=2))
    #2023-03-28


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


def download_file_using_curl(file_url, file_path):
    cmd = f'curl -o "{file_path}" "{file_url}"'
    print(cmd)
    os.system(cmd)


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
# {
#   "corpusid": 254640939,
#   "externalids": {
#     "arxiv": null,
#     "mag": null,
#     "acl": null,
#     "pubmed": "36589072",
#     "pubmedcentral": "9798118",
#     "dblp": null,
#     "doi": "10.3389/fpls.2022.1074889"
#   },
#   "content": {
#     "source": {
#       "pdfurls": null,
#       "pdfsha": "b57a70144c90672103cea4f8ca8023ac9fab337b",
#       "oainfo": null
#     },
#     "text": "\nGrafting promoted antioxidant capacity and carbon and nitrogen metabolism of bitter gourd seedlings under heat stress OPEN ACCESS EDITED BY\n15 December 2022\n\nLe Liang \nCollege of Horticulture\nSichuan Agricultural University\nChengduS
# n",
#     "annotations": {
#       "abstract": "[{\"end\":5011,\"start\":2938}]",
#       "author": "[{\"end\":245,\"start\":159},{\"end\":332,\"start\":246},{\"end\":335,\"start\":333},{\"end\":431,\"start\":336},{\"end\":516,\"start\":432},{\"end\":604,\"start\":517},{\"end\":617,\"start\":605},{\"end\":849,\"start\":618},{\"end\":1009,\"start\":850},{\"end\":1316,\"start\":1010},{\"end\":1620,\"start\":1317},{\"end\":1634,\"start\":1621},{\"end\":1651,\"start\":1635},{\"end\":1667,\"start\":1652},{\"end\":1675,\"start\":1668},{\"end\":1688,\"start\":1676},{\"end\":1700,\"start\":1689},{\"end\":1709,\"start\":1701},{\"end\":1718,\"start\":1710},{\"end\":1726,\"start\":1719},{\"end\":1734,\"start\":1727},{\"end\":1741,\"start\":1735},{\"end\":1750,\"start\":1742},{\"end\":1760,\"start\":1751},{\"end\":1763,\"start\":1761},{\"end\":1769,\"start\":1764},{\"end\":1775,\"start\":1770},{\"end\":1783,\"start\":1776}]",
#       "figureref": "[{\"end\":18398,\"start\":18390},{\"attributes\":{\"ref_id\":\"fig_1\"},\"end\":19729,\"start\":19720},{\"end\":20965,\"start\":20956},{\"attributes\":{\"ref_id\":\"fig_2\"},\"end\":22058,\"start\":22048},{\"attributes\":{\"ref_id\":\"fig_3\"},\"end\":23687,\"start\":23679},{\"attributes\":{\"ref_id\":\"fig_4\"},\"end\":24645,\"start\":24636},{\"attributes\":{\"ref_id\":\"fig_6\"},\"end\":25416,\"start\":25384},{\"attributes\":{\"ref_id\":\"fig_7\"},\"end\":26237,\"start\":26229}]",
#       "formula": null,
#       "paragraph": "[{\"end\":7216,\"start\":5027},{\"end\":9256,\"start\":7218},{\"end\":10613,\"start\":9258},{\"end\":11863,\"start\":10615},{\"end\":12418,\"start\":11901},{\"end\":12693,\"start\":12442},{\"end\":13193,\"start\":12695},{\"end\":13960,\"start\":13195},{\"end\":15156,\"start\":13962},{\"end\":15850,\"start\":15247},{\"end\":16425,\"start\":15882},{\"end\":16742,\"start\":16477},{\"end\":17074,\"start\":16744},{\"end\":17645,\"start\":17128},{\"end\":18084,\"start\":17670},{\"end\":19481,\"start\":18146},{\"end\":20528,\"start\":19517},{\"end\":21730,\"start\":20558},{\"end\":23405,\"start\":21772},{\"end\":24438,\"start\":23445},{\"end\":25212,\"start\":24482},{\"end\":25677,\"start\":25261},{\"end\":26063,\"start\":25679},{\"end\":26238,\"start\":26065},{\"end\":27450,\"start\":26253},{\"end\":31065,\"start\":27452},{\"end\":33813,\"start\":31067},{\"end\":36731,\"start\":33815},{\"end\":37883,\"start\":36747},{\"end\":38081,\"start\":37915},{\"end\":38549,\"start\":38106}]",
#       "publisher": null,
#       "sectionheader": "[{\"attributes\":{\"n\":\"1\"},\"end\":5025,\"start\":5013},{\"attributes\":{\"n\":\"2\"},\"end\":11887,\"start\":11866},{\"attributes\":{\"n\":\"2.1\"},\"end\":11899,\"start\":11890},{\"attributes\":{\"n\":\"2.2\"},\"end\":12440,\"start\":12421},{\"attributes\":{\"n\":\"2.3\"},\"end\":15245,\"start\":15159},{\"attributes\":{\"n\":\"2.3.2\"},\"end\":15880,\"start\":15853},{\"attributes\":{\"n\":\"2.3.3\"},\"end\":16475,\"start\":16428},{\"attributes\":{\"n\":\"2.3.4\"},\"end\":17126,\"start\":17077},{\"attributes\":{\"n\":\"2.4\"},\"end\":17668,\"start\":17648},{\"attributes\":{\"n\":\"3\"},\"end\":18094,\"start\":18087},{\"attributes\":{\"n\":\"3.1\"},\"end\":18144,\"start\":18097},{\"attributes\":{\"n\":\"3.2\"},\"end\":19515,\"start\":19484},{\"attributes\":{\"n\":\"3.3\"},\"end\":20556,\"start\":20531},{\"attributes\":{\"n\":\"3.4\"},\"end\":21770,\"start\":21733},{\"end\":23413,\"start\":23408},{\"attributes\":{\"n\":\"3.5\"},\"end\":23443,\"start\":23416},{\"attributes\":{\"n\":\"3.6\"},\"end\":24480,\"start\":24441},{\"attributes\":{\"n\":\"3.7\"},\"end\":25259,\"start\":25215},{\"attributes\":{\"n\":\"4\"},\"end\":26251,\"start\":26241},{\"attributes\":{\"n\":\"5\"},\"end\":36745,\"start\":36734},{\"end\":37913,\"start\":37886},{\"end\":38104,\"start\":38084},{\"end\":39116,\"start\":39108},{\"end\":39312,\"start\":39304},{\"end\":39332,\"start\":39324},{\"end\":39588,\"start\":39580},{\"end\":40549,\"start\":40541},{\"end\":40569,\"start\":40561}]",
#       "table": null,
#       "tableref": null,
#       "title": "[{\"end\":140,\"start\":1},{\"end\":1923,\"start\":1784}]",
#       "venue": "[{\"end\":1941,\"start\":1925}]"
#     }
#   }
# }



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
        download_file_using_curl(file_url, file_path)

    for file_name in os.listdir(dataset_folder):
        print(f'Inspecting {file_name}...')
        file_path = dataset_folder / file_name
        inspect_s2orc_file(file_path)


if __name__ == '__main__':
    #test_papers()
    test_s2orc()


