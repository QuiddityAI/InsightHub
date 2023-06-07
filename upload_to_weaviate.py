import csv
from pathlib import Path
import time
import uuid

import weaviate
import numpy as np


weaviate_server_url = "http://localhost:8080"
data_root = Path('/media/tim/Exchange/pubmed_embeddings/')
embeddings_path = data_root / 'PubMedBERT_embeddings_float16.npy'
master_data_path = data_root / 'pubmed_landscape_data.csv'
item_class_name = "Paper"
max_items = 200000


client = weaviate.Client(
    url = weaviate_server_url,
    # using anonymous connection, no auth needed
    # auth_client_secret=weaviate.AuthApiKey(api_key="YOUR-WEAVIATE-API-KEY"),
)

def initial_setup():
    class_obj = {
        "class": item_class_name,
        "vectorizer": "none",
    }

    try:
        client.schema.create_class(class_obj)
    except weaviate.exceptions.UnexpectedStatusCodeException as e:
        print(e)


def add_data():
    # Load data
    # TODO

    embeddings = np.load(embeddings_path, mmap_mode='r')
    # print(embeddings[0])

    begin = time.time()

    # Configure a batch process
    with client.batch(batch_size=100) as batch:
        # Batch import all Paper
        with open(master_data_path, newline='') as csvfile:
            csvreader = csv.DictReader(csvfile)
            
            for i, row in enumerate(csvreader):
                # print(f"importing paper: {i+1}")
                # print(row['Title'][:30])
                # print(embeddings[i][0], len(embeddings[i]))

                properties = {
                    "title": row["Title"],
                    "journal": row["Journal"],
                    "pmid": row["PMID"],
                    "year": row["Year"],
                    "labels": row["Labels"],
                    "colors": row["Colors"],
                }

                # generate a consistent uuid from the PMID of the paper:
                id = uuid.uuid3(uuid.NAMESPACE_URL, row["PMID"])

                batch.add_data_object(
                    properties,
                    item_class_name,
                    vector=embeddings[i],
                    uuid=id,
                )
                # if "batch" if full now, it will flush the data and reset (?)

                if i >= max_items:
                    break

    end = time.time()
    total_time = end - begin
    print(f"Total time: {total_time:.1f} s, time per item: {(total_time * 1000) / max_items:.2f} ms")
    # For 20'000 items and batch size 100:
    # Total time: 329.6 s, time per item: 1.65 ms

# {'error': [{'message': 'update prop-specific indices: store is read-only'}]}
# {'error': [{'message': 'store is read-only'}]}

"""
Example GraphQL query:

Go to: https://console.weaviate.cloud/query

{
  Get {
    Paper(
      limit: 3
      bm25: {
        query: "food"
      }
    ) {
      title
      pmid
      journal
    }
  }
}


"""

if __name__ == "__main__":
    # initial_setup()
    add_data()
