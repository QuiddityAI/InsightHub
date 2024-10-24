import csv
import requests

from ingest.schemas import UploadedOrExtractedFile
from ingest.logic.common import UPLOADED_FILES_FOLDER


def import_csv(paths: list[UploadedOrExtractedFile], parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    if '__all__' not in parameters.get("fields", []):
        # TODO: implement custom field set
        raise ValueError("custom field set not yet implemented for csv import")

    for uploaded_file in paths:
        csv_reader = csv.DictReader(open(f'{UPLOADED_FILES_FOLDER}/{uploaded_file.local_path}', 'r'))
        for i, row in enumerate(csv_reader):
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            items.append(row)
        if on_progress:
            on_progress(0.5 + (len(items) / len(paths)) * 0.5)

    return items, []


def import_website_url(raw_items, parameters, on_progress=None) -> tuple[list[dict], list[dict]]:
    items = []
    for raw_item in raw_items:
        url = raw_item.get("url")
        # get title from url using web scraping
        headers = {'headers':'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}
        result = requests.get(url, headers=headers)
        html = result.text
        title = html[html.find('<title>') + 7 : html.find('</title>')]
        items.append({
            "url": url,
            "title": title,
            "content": html,
        })

        if on_progress:
            on_progress(0.5 + (len(items) / len(raw_items)) * 0.5)

    return items, []