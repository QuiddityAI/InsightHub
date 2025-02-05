import logging
import time

import tqdm
import orjson

from data_backend_client import update_database_layout, insert_many


# see https://github.com/shuttie/esci-s

"""
{
  "type": "product",
  "locale": "us",
  "asin": "B06XXXLJ6V",
  "title": "FYY Leather Case with Mirror for Samsung Galaxy S8 Plus, Leather Wallet Flip Folio Case with Mirror and Wrist Strap for Samsung Galaxy S8 Plus Black",
  "stars": "4.3 of 5 stars",
  "ratings": "1,116",
  "category": [
    "Cell Phones & Accessories",
    "Cases, Holsters & Sleeves",
    "Flip Cases"
  ],
  "attrs": {
    "Material": "Faux Leather",
    "Compatible Phone Models": "Samsung Galaxy S8 Plus",
    "Form Factor": "Flip",
    "Brand": "FYY",
    "Color": "Black"
  },
  "bullets": [
    "RFID Technique: Radio Frequency Identification technology, through radio signals to identify specific targets and to read and copy electronic data. Most Credit Cards, Debit Cards, ID Cards are set-in the RFID chip, the RFID reader can easily read the cards information within 10 feet(about 3m) without touching them. This case is designed to protect your cards information from stealing with blocking material of RFID shielding technology.",
    "Unique design. Cosmetic Mirror inside made for your makeup and beauty.",
    "Card slots provide you to put debit card, credit card or ID card while on the go.",
    "High quality. Made with Premium PU Leather. Kickstand function is convenient for movie-watching or video-chatting.",
    "Perfect gift for Mother's Day, Father's Day, Valentine's Day, Thanksgiving Day and Christmas."
  ],
  "description": "Product Description Premium PU Leather Top quality. Made with Premium PU Leather. Receiver design. Accurate cut-out for receiver. Convenient to Answer the phone without open the case. Hand strap makes it easy to carry around. RFID Technique RFID Technique: Radio Frequency Identification technology, through radio signals to identify specific targets and to read and copy electronic data. Most Credit Cards, Debit Cards, ID Cards are set-in the RFID chip, the RFID reader can easily read the cards information within 10 feet(about 3m) without touching them. This case is designed to protect your cards information from stealing with blocking material of RFID shielding technology. 100% Handmade 100% Handmade. Perfect craftmanship and reinforced stitching makes it even more durable. Sleek, practical and elegant with a variety of dashing colors. Multiple Functions Card slots are designed for you to put your photo, debit card, credit card or ID card while on the go. Unique design. Cosmetic Mirror inside made for your makeup and beauty. Perfect Viewing Angle. Kickstand function is convenient for movie-watching or video-chatting. Space amplification, convenient to unlock. Kickstand function is convenient for movie-watching or video-chatting. ",
  "info": {
    "Included Components": "Kickstand",
    "Best Sellers Rank": "#141,895 in Cell Phones & Accessories ( See Top 100 in Cell Phones & Accessories ) #10,494 in Flip Cell Phone Cases",
    "Colour": "Black",
    "Product Dimensions": "15.99 x 8.99 x 1 inches",
    "Manufacturer": "GUANGZHOU WENYI COMMUNICATION EQIPMENT CO.,LTD",
    "Item Weight": "0.023 ounces",
    "Date First Available": "March 30, 2017",
    "ASIN": "B06XXXLJ6V",
    "Item model number": "4326500860",
    "Customer Reviews": "4.3 out of 5 stars 1,116 ratings 4.3 out of 5 stars",
    "Is Discontinued By Manufacturer": "No",
    "Form Factor": "Flip",
    "Other display features": "Wireless"
  },
  "reviews": [
    {
      "stars": "3.0 of 5 stars",
      "title": "very cute but....",
      "date": "Reviewed in the United States 🇺🇸 on September 22, 2022",
      "text": "very cute but didn't last long at all"
    }, ...
  ],
  "price": "",
  "formats": {},
  "template": "wireless",
  "image": "https://m.media-amazon.com/images/I/81bdoltQWVL.__AC_SY300_SX300_QL70_FMwebp_.jpg"
  Note: apparently its sometimes called "img"
}
"""


def preprocess_item(raw_item: dict) -> dict:
    raw_item["stars"] = float(raw_item["stars"].split(" ")[0]) if "stars" in raw_item and raw_item["stars"] else None
    raw_item["ratings"] = (
        int(raw_item["ratings"].split(" ")[0].replace(",", ""))
        if "ratings" in raw_item and raw_item["ratings"]
        else None
    )
    if "review" in raw_item:
        if isinstance(raw_item["review"], dict):
            raw_item["reviews"] = raw_item["review"]
        del raw_item["review"]
    for review in raw_item.get("reviews", []):
        review["stars"] = float(review["stars"].split(" ")[0]) if "stars" in review else None
        review["text"] = review["title"] + "; " + review["text"]
        del review["title"]
        del review["date"]
    if "img" in raw_item and not "image" in raw_item:
        raw_item["image"] = raw_item["img"]
        del raw_item["img"]
    if "attr" in raw_item:
        raw_item["attrs"] = raw_item["attr"]
        del raw_item["attr"]
    if "desc" in raw_item:
        raw_item["description"] = raw_item["desc"]
        del raw_item["desc"]
    if (
        "price" in raw_item
        and isinstance(raw_item["price"], str)
        and raw_item["price"] != ""
        and "$" in raw_item["price"]
    ):
        try:
            raw_item["price"] = float(raw_item["price"].split(" ")[0].replace("$", "").replace(",", ""))
        except ValueError as e:
            print(e)
            print(raw_item["price"])
            raw_item["price"] = None
    else:
        raw_item["price"] = None
    if "info" in raw_item:
        del raw_item["info"]
    if "formats" in raw_item:
        del raw_item["formats"]
    if "template" in raw_item:
        del raw_item["template"]
    if "author" in raw_item:
        del raw_item["author"]
    if "subtitle" in raw_item:
        del raw_item["subtitle"]
    return raw_item


def import_dataset():
    dataset_id = 7
    update_database_layout(dataset_id)

    max_items = 1700000

    items = []
    total_items = 0

    with open("/data/amazon_esci_s_1_6M/esci.json", "r") as f:
        for row in tqdm.tqdm(f, total=max_items):
            raw_item = orjson.loads(row)
            if raw_item.get("locale") not in ("en", "us"):
                continue
            if "img" not in raw_item and "image" not in raw_item:
                continue
            item = preprocess_item(raw_item)
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
        if items:
            t1 = time.time()
            insert_many(dataset_id, items)
            t2 = time.time()
            print(f"Duration: {t2 - t1:.3f}s, time per item: {((t2 - t1)/len(items))*1000:.2f} ms")


if __name__ == "__main__":
    import_dataset()
