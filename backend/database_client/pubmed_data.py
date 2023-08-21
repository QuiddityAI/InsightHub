import mmap
from pathlib import Path
import pickle

import requests


data_root = Path('/data/pubmed_embeddings/')
abstracts_path = data_root / 'pubmed_landscape_abstracts.csv'

pmid_to_abstract_pos_and_length = None
abstracts_mmap_file = None


def load_pubmed_data():
    global pmid_to_abstract_pos_and_length, abstracts_mmap_file

    with open(data_root / "pmid_to_pos_and_length.pkl", "rb") as f:
        pmid_to_abstract_pos_and_length = pickle.load(f)

    with open(abstracts_path, "r+") as f:
        abstracts_mmap_file = mmap.mmap(f.fileno(), 0)


def get_pubmed_abstract(pmid):
    if pmid_to_abstract_pos_and_length is None:
        load_pubmed_data()
    pos, length = pmid_to_abstract_pos_and_length[pmid]
    abstract = abstracts_mmap_file[pos : pos + length].decode()
    abstract = abstract.strip('"')
    return abstract


def get_pubmed_abstract_online(pmid: str):
    try:
        result = requests.get(f"http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=text&rettype=abstract")
        raw_xml = result.text
        abstract = raw_xml  # .split("<AbstractText>")[1].split("</AbstractText>")[0]
    except IndexError:
        return ""
    except Exception as e:
        print(e)
        return ""
    return abstract