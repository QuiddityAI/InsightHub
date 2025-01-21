from pathlib import Path
import random
import re
import sys
import pickle
import mmap
import gzip
import time

import orjson
from tqdm import tqdm
import cbor2

from download_semantic_scholar_dataset import DatasetNames

file_id_to_path = {}
corpusid_to_file_pos_and_length = {}


def append_index(file_path: Path):
    global file_id_to_name, corpusid_to_file_pos_and_length
    t1 = time.time()

    current_pos = 0
    corpusid_regex = re.compile(rb'"corpusid":(\d+),')

    file_id = len(file_id_to_path)
    file_id_to_path[file_id] = file_path

    # with gzip.open(file_path, 'rt', encoding='utf-8') as f:
    with open(file_path, "rb") as f:
        for line in f:
            assert isinstance(line, bytes)
            corpusid = int(corpusid_regex.search(line).group(1))  # type: ignore
            corpusid_to_file_pos_and_length[corpusid] = (file_id, current_pos, len(line))
            current_pos += len(line)  # including newline

    t2 = time.time()
    print(f"done in {t2 - t1:.2f} seconds")

    print("done")


def test(index_file_path):
    print("testing...")

    with open(index_file_path, "rb") as f:
        file_id_to_path, corpusid_to_file_pos_and_length = pickle.load(f)
        # file_id_to_path, corpusid_to_file_pos_and_length = cbor2.load(f)

    corpusid = random.choice(list(corpusid_to_file_pos_and_length.keys()))

    t3 = time.time()
    file_id, pos1, length1 = corpusid_to_file_pos_and_length[corpusid]
    print(f"corpusid: {corpusid}, pos: {pos1}, length: {length1}")

    file_path = file_id_to_path[file_id]

    # with gzip.open(file_path, 'rt', encoding='utf-8') as f:
    with open(file_path, "rb") as f:
        f.seek(pos1)
        line = f.readline()
        print(line)
        assert len(line) == length1
        data = orjson.loads(line)
        print(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode())

    t4 = time.time()
    print(f"done in {(t4 - t3) * 1000:.1f} ms")


def save(index_file_path):
    print("saving...")

    data = (file_id_to_path, corpusid_to_file_pos_and_length)

    with open(index_file_path, "wb") as f:
        pickle.dump(data, f)
        # cbor2.dump(data, f)  # not much smaller, but slighly slower


def build_index_for_dataset(dataset_name: str):
    base_download_folder = f"/data/semantic_scholar"
    dataset_folder = Path(base_download_folder) / dataset_name
    files = list(dataset_folder.glob("*"))
    for file in files:
        index_file_path = file.with_suffix(".index.pkl")
        append_index(file)

    index_file_path = Path(base_download_folder) / f"{dataset_name}.index.pkl"
    save(index_file_path)
    test(index_file_path)


def convert_to_flat_index():
    import numpy as np

    base_download_folder = f"/data/semantic_scholar"
    abstract_file_paths, abstract_index = pickle.load(open(Path(base_download_folder) / f"abstracts.index.pkl", "rb"))
    print(f"Loaded")
    corpus_ids = np.array(list(abstract_index.keys()))
    corpus_ids.sort()
    file_ids = np.array([abstract_index[corpus_id][0] for corpus_id in corpus_ids])
    file_positions = np.array([abstract_index[corpus_id][1] for corpus_id in corpus_ids])
    print(f"Converted")
    with open(Path(base_download_folder) / f"abstracts.flat_index.pkl", "wb") as f:
        pickle.dump((abstract_file_paths, corpus_ids, file_ids, file_positions), f)
    print(f"Saved")


if __name__ == "__main__":
    # build_index_for_dataset(DatasetNames.TLDRS)
    # build_index_for_dataset(DatasetNames.ABSTRACTS)
    convert_to_flat_index()
