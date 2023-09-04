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

from database_client.django_client import get_object_schema
from logic.extract_pipeline import get_pipeline_steps
from logic.insert_logic import insert_many, update_database_layout
from database_client.vector_search_engine_client import VectorSearchEngineClient

from utils.custom_json_encoder import CustomJSONEncoder

logging.root.setLevel(logging.INFO)


def test_schema_serialization():
    schema = get_object_schema(3)

    print(json.dumps(schema, indent=4, cls=CustomJSONEncoder))

    steps = get_pipeline_steps(schema)

    print(json.dumps(steps, indent=4, cls=CustomJSONEncoder))

    return schema


def test_vector_db_client(schema):
    vse_client = VectorSearchEngineClient()

    vector_field = 'openai_vector'

    # vse_client.remove_schema(schema.id, vector_field)
    vse_client.ensure_schema_exists(schema, vector_field)

    item = {
        "description": "White crew neck t-shirt",
        "year": 2017,
    }

    vse_client.upsert_items(schema.id, vector_field, [32, 34], [item, item], [[4, 5, 6, 7]]*2)

    items = vse_client.get_items_near_vector(schema.id, vector_field, [7, 8, 4, 5], {}, limit=5)
    print(items)


def test_insert_many_books():
    schema_id = 4
    update_database_layout(schema_id)

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
                insert_many(schema_id, elements)
                t2 = time.time()
                print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(elements))*1000:.2f} ms")
                elements = []


def test_insert_many_fashion():
    schema_id = 5
    update_database_layout(schema_id)

    elements = []
    max_elements = 10000
    counter = 0

    # see here: https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset
    with open('/data/kaggle_fashion_44k/styles.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in tqdm.tqdm(reader, total=max_elements):
            row['image'] = f'/data/kaggle_fashion_44k/images/{row["id"]}.jpg'
            elements.append(row)
            counter += 1
            if counter >= max_elements:
                break

            if counter % 512 == 0:
                t1 = time.time()
                insert_many(schema_id, elements)
                t2 = time.time()
                print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(elements))*1000:.2f} ms")
                elements = []


if __name__ == "__main__":
    # schema = test_schema_serialization()
    # test_vector_db_client(schema)
    # test_insert_many_books()
    test_insert_many_fashion()

