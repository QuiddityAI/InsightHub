import logging
import time
import gzip
import json
import sys
import csv

import tqdm
import orjson

from data_backend_client import update_database_layout, insert_many, files_in_folder

sys.path.append("../../data_backend/")
from utils.dotdict import DotDict


"""
{
  "item_dimensions": {
    "height": {
      "normalized_value": {
        "unit": "inches",
        "value": 2.99
      },
      "unit": "inches",
      "value": 2.99
    },
    "length": {
      "normalized_value": {
        "unit": "inches",
        "value": 9.21
      },
      "unit": "inches",
      "value": 9.21
    },
    "width": {
      "normalized_value": {
        "unit": "inches",
        "value": 8.31
      },
      "unit": "inches",
      "value": 8.31
    }
  },
  "brand": [
    {
      "language_tag": "en_AE",
      "value": "AmazonBasics"
    }
  ],
  "bullet_point": [
    {
      "language_tag": "en_AE",
      "value": "3D printer filament with 1.75mm diameter + / - .05mm; designed to fit most common 3D printers (check spool size for compatibility); Translucent Yellow; 1 kg spool"
    },
    {
      "language_tag": "en_AE",
      "value": "Made of PETG plastic, known for its ease of use (like PLA) and durable strength (like ABS); no heating bed needed; offers easy bed adhesion, stiffness, and a glossy finish"
    },
    {
      "language_tag": "en_AE",
      "value": "Spool's built-in gauge shows percentage of material remaining and approximate length remaining"
    },
    {
      "language_tag": "en_AE",
      "value": "Engineered to reduce jamming; resealable storage bag included to protect filament between use"
    },
    {
      "language_tag": "en_AE",
      "value": "Measures 9.2 by 8.3 by 3 inches (LxWxH); weighs 2.2 pounds; backed by an AmazonBasics 1-year limited warranty"
    }
  ],
  "color": [
    {
      "language_tag": "en_AE",
      "value": "Translucent Yellow"
    }
  ],
  "item_id": "B07H9GMYXS",
  "item_name": [
    {
      "language_tag": "en_AE",
      "value": "AmazonBasics PETG 3D Printer Filament, 1.75mm, 1 kg Spool 1.75mm AMG10528516-10"
    }
  ],
  "item_weight": [
    {
      "normalized_value": {
        "unit": "pounds",
        "value": 2.2
      },
      "unit": "pounds",
      "value": 2.2
    }
  ],
  "material": [
    {
      "language_tag": "en_AE",
      "value": "PETG (Polyethylene Terephtalate Glycol-modified)"
    }
  ],
  "model_number": [
    {
      "value": "AMG10528516-10"
    }
  ],
  "product_type": [
    {
      "value": "MECHANICAL_COMPONENTS"
    }
  ],
  "style": [
    {
      "language_tag": "en_AE",
      "value": "1-Pack"
    }
  ],
  "main_image_id": "81NP7qh2L6L",
  "other_image_id": [
    "81A0u5L4VAL",
    "61xhS6iLrZL"
  ],
  "item_keywords": [
    {
      "language_tag": "en_AE",
      "value": "3d printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "petg printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "petg filament"
    },
    {
      "language_tag": "en_AE",
      "value": "1.75mm printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "1kg spool printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "translucent yellow printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "1kg printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "translucent yellow 3D printer filament"
    },
    {
      "language_tag": "en_AE",
      "value": "petg 3D printer filament"
    }
  ],
  "country": "AE",
  "marketplace": "Amazon",
  "domain_name": "amazon.ae",
  "node": [
    {
      "node_id": 11601270031,
      "node_name": "/Categories"
    }
  ]
}
"""


def preprocess_item(raw_item: DotDict, image_id_to_path) -> dict:
    item = {
        "asin": raw_item.item_id,
        "name": raw_item.item_name[0].value if raw_item.item_name else None,
        "description": raw_item.product_description[0].value if raw_item.product_description else None,
        "bullet_points": [e["value"] for e in raw_item.bullet_point if e["language_tag"].startswith("en_")]
        if raw_item.bullet_point
        else None,
        "keywords": list({e["value"] for e in raw_item.item_keywords if e["language_tag"].startswith("en_")})
        if raw_item.item_keywords
        else None,
        "image": image_id_to_path[raw_item.main_image_id] if raw_item.main_image_id else None,
        "other_images": [image_id_to_path[e] for e in raw_item.other_image_id] if raw_item.other_image_id else None,
        "category": raw_item.product_type[0].value if raw_item.product_type else None,
        "attributes": {
            "material": raw_item.material[0].value if raw_item.material else None,
            "fabric": raw_item.fabric_type[0].value if raw_item.fabric_type else None,
            "pattern": raw_item.pattern[0].value if raw_item.pattern else None,
            "style": raw_item.style[0].value if raw_item.style else None,
            "color": raw_item.color[0].value if raw_item.color else None,
            "brand": raw_item.brand[0].value if raw_item.brand else None,
        },
        "country": raw_item.country,
    }
    return item


def import_dataset():
    dataset_id = 8
    update_database_layout(dataset_id)

    max_items = 10000000

    items = []
    total_items = 0

    image_id_to_path = {}
    with gzip.open("/data/amazon_products_berkeley/images/metadata/images.csv.gz", "r") as f:
        for row in f:
            row = row.decode().strip()
            row = row.split(",")
            image_id_to_path[row[0]] = "/data/amazon_products_berkeley/images/small/" + row[3]

    gz_files = files_in_folder("/data/amazon_products_berkeley/listings/metadata")

    for filename in tqdm.tqdm(gz_files):
        with gzip.open(filename, "r") as f:
            for line in tqdm.tqdm(f):
                try:
                    raw_item = orjson.loads(line)
                except json.decoder.JSONDecodeError as e:
                    logging.error(repr(e))
                    continue
                raw_item = DotDict(raw_item)
                if raw_item.country not in ("US", "AE", "GB", "CA", "IN"):
                    continue
                item = preprocess_item(raw_item, image_id_to_path)
                # print(json.dumps(item, indent=2, ensure_ascii=False))
                # break

                items.append(item)
                total_items += 1

                if total_items % 512 == 0:
                    t1 = time.time()
                    insert_many(dataset_id, items)
                    t2 = time.time()
                    print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(items))*1000:.2f} ms")
                    items = []
                if total_items >= max_items:
                    break
        if total_items >= max_items:
            break

    if items:
        t1 = time.time()
        insert_many(dataset_id, items)
        t2 = time.time()
        print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(items))*1000:.2f} ms")


if __name__ == "__main__":
    import_dataset()
