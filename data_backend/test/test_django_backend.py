"""
Run with "python3 -m test.test_django_backend"
"""

import json
import time
import csv
import logging
from typing import Callable

import tqdm
from utils.dotdict import DotDict

from database_client.django_client import get_dataset
from logic.extract_pipeline import get_pipeline_steps
from logic.insert_logic import insert_many, update_database_layout
from database_client.vector_search_engine_client import VectorSearchEngineClient

from utils.custom_json_encoder import CustomJSONEncoder

logging.root.setLevel(logging.INFO)


def test_dataset_serialization():
    dataset = get_dataset(3)

    print(json.dumps(dataset, indent=4, cls=CustomJSONEncoder))

    steps_and_fields = get_pipeline_steps(dataset)

    print(json.dumps(steps_and_fields, indent=4, cls=CustomJSONEncoder))

    return dataset


def test_vector_db_client(dataset):
    vse_client = VectorSearchEngineClient()

    vector_field = 'openai_vector'

    # vse_client.remove_dataset(dataset.id, vector_field)
    vse_client.ensure_dataset_exists(dataset, vector_field)

    item = {
        "description": "White crew neck t-shirt",
        "year": 2017,
    }

    vse_client.upsert_items(dataset.id, vector_field, [32, 34], [item, item], [[4, 5, 6, 7]]*2)

    items = vse_client.get_items_near_vector(dataset.id, vector_field, [7, 8, 4, 5], {}, limit=5)
    print(items)


def test_insert_many_books():
    dataset_id = 4
    update_database_layout(dataset_id)

    elements = []
    max_elements = 300000
    counter = 0

    # see here: https://www.kaggle.com/datasets/mohamedbakhet/amazon-books-reviews?select=books_data.csv
    with open('/data/kaggle_amazon_book_reviews_3M/books_data.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in tqdm.tqdm(reader, total=240000):
            #print(json.dumps(row, indent=4))
            #break
            try:
                row['authors'] = json.loads(row['authors'].replace("'", '"')) if row['authors'] else []
                row['categories'] = json.loads(row['categories'].replace("'", '"')) if row['categories'] else []
            except json.decoder.JSONDecodeError:
                print("Json decode error")
                continue
            elements.append(row)
            counter += 1
            if counter >= max_elements:
                break

            if counter % 512 == 0:
                t1 = time.time()
                insert_many(dataset_id, elements)
                t2 = time.time()
                print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(elements))*1000:.2f} ms")
                elements = []


def test_insert_many_fashion():
    dataset_id = 5
    update_database_layout(dataset_id)

    elements = []
    max_elements = 45000
    counter = 0

    # see here: https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset
    with open('/data/kaggle_fashion_44k/styles.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in tqdm.tqdm(reader, total=max_elements):
            row['image'] = f'/data/kaggle_fashion_44k/images/{row["id"]}.jpg'
            elements.append(row)
            counter += 1

            if counter % min(max_elements, 512) == 0:
                t1 = time.time()
                insert_many(dataset_id, elements)
                t2 = time.time()
                print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(elements))*1000:.2f} ms")
                elements = []

            if counter >= max_elements:
                break


if __name__ == "__main__":
    # dataset = test_dataset_serialization()
    # test_vector_db_client(dataset)
    test_insert_many_books()
    # test_insert_many_fashion()

