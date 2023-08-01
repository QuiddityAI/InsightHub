import csv
from pathlib import Path
import time
import uuid
import sys
import datetime

import weaviate
import numpy as np

if sys.platform == "darwin":
    # Macbook
    data_root = Path('/Users/tim/vector-search/pubmed_embeddings/')
else:
    # Desktop
    data_root = Path('/data/pubmed_embeddings/')


weaviate_server_url = "http://localhost:8080"
embeddings_path = data_root / 'PubMedBERT_embeddings_float16.npy'
master_data_path = data_root / 'pubmed_landscape_data.csv'
item_class_name = "Paper"
offset = 2630001
max_items = 5000000 - 2630001


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

    embeddings = np.load(embeddings_path, mmap_mode='r')
    # print(embeddings[0])

    begin = time.time()
    actual_count = 0

    try:
        # Configure a batch process
        with client.batch(batch_size=100) as batch:
            # Batch import all Paper
            with open(master_data_path, newline='') as csvfile:
                csvreader = csv.DictReader(csvfile)

                for i, row in enumerate(csvreader):
                    if i < offset:
                        continue

                    if i%10000 == 1 and actual_count:
                        print(f"{100*((i-offset)/max_items):.1f} %, {i-offset} of {max_items} (current index: {i}) ")
                        total_time = time.time() - begin
                        time_per_item_sec = total_time / actual_count
                        time_left_min = ((max_items - actual_count) * time_per_item_sec) / 60.0
                        wall_time_end = datetime.datetime.now() + datetime.timedelta(minutes=time_left_min)
                        print(f"Time left: {time_left_min:.1f} min ({wall_time_end.time().isoformat(timespec='minutes')}), time per item: {time_per_item_sec * 1000:.2f} ms")


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
                        "source_index": i,
                    }

                    # generate a consistent uuid from the PMID of the paper:
                    id = uuid.uuid3(uuid.NAMESPACE_URL, row["PMID"])

                    batch.add_data_object(
                        properties,
                        item_class_name,
                        vector=embeddings[i],
                        uuid=id,
                    )
                    # if "batch" is full now, it will flush the data and reset (?)

                    actual_count += 1

                    if (i - offset) >= max_items:
                        break
    except KeyboardInterrupt:
        pass

    end = time.time()
    total_time = end - begin
    print(f"Total time: {total_time:.1f} s, time per item: {(total_time * 1000) / actual_count:.2f} ms, items added: {actual_count}")
    # For 200'000 items and batch size 100:
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
