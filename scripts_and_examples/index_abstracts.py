from pathlib import Path
import re
import sys
import pickle
import mmap

from tqdm import tqdm

if sys.platform == "darwin":
    # Macbook
    data_root = Path("/Users/tim/vector-search/pubmed_embeddings/")
else:
    # Desktop
    data_root = Path("/data/pubmed_embeddings/")


abstracts_path = data_root / "pubmed_landscape_abstracts.csv"

pmid_to_pos_and_length = {}

with open(abstracts_path, "r+") as f:
    data = mmap.mmap(f.fileno(), 0)
    for match in tqdm(re.finditer(rb"^([0-9]+),(.*)$", data, flags=re.MULTILINE), total=26000000):
        pmid = match.group(1)
        pos_of_abstract_start = match.start() + len(pmid) + 1
        abstract_length = len(match.group(2))  # including quotes
        pmid_to_pos_and_length[pmid.decode()] = (pos_of_abstract_start, abstract_length)

print("saving...")

with open(data_root / "pmid_to_pos_and_length.pkl", "wb") as f:
    pickle.dump(pmid_to_pos_and_length, f)

print("done")

print("testing...")

with open(data_root / "pmid_to_pos_and_length.pkl", "rb") as f:
    x = pickle.load(f)

pos1, length1 = x["1133453"]

with open(abstracts_path, "r+") as f:
    data = mmap.mmap(f.fileno(), 0)
    abstract = data[pos1 : pos1 + length1].decode()

print(abstract)

print("done")
