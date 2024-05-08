import logging
from typing import Iterable

from utils.field_types import FieldType
from utils.dotdict import DotDict

from database_client.django_client import get_collection, get_collection_items, get_dataset, get_export_converter
from database_client.text_search_engine_client import TextSearchEngineClient

from logic.search_common import get_document_details_by_id


def export_item(dataset_id: int, item_id: int, export_converter_identifier: str) -> dict:
    converter_definition = get_export_converter(export_converter_identifier)
    converter = get_export_converter_module(converter_definition.module, converter_definition.parameters)
    required_fields = converter.required_fields()
    if "__all__" in required_fields:
        dataset = get_dataset(dataset_id)
        required_fields = dataset.object_fields.keys()
    item = get_document_details_by_id(dataset_id, item_id, required_fields)
    if not item:
        return { "value": None, "error": "Item not found"}
    item = DotDict(item)
    exported_data = converter.export_single(item)
    return exported_data


def export_collection(collection_id: int, class_name: str, export_converter_identifier: str) -> dict:
    converter_definition = get_export_converter(export_converter_identifier)
    converter = get_export_converter_module(converter_definition.module, converter_definition.parameters)
    required_fields = converter.required_fields()

    collection = get_collection(collection_id)
    if not collection:
        return { "value": None, "error": "Collection not found"}
    collection_items = get_collection_items(collection_id, class_name, field_type=None, is_positive=None)
    item_ids_by_dataset = {}
    for i, item in enumerate(collection_items):
        if item['field_type'] != FieldType.IDENTIFIER:
            continue
        dataset_id = item['dataset_id']
        item_id = item['item_id']
        if dataset_id not in item_ids_by_dataset:
            item_ids_by_dataset[dataset_id] = []
        item_ids_by_dataset[dataset_id].append(item_id)

    all_items = []
    search_engine_client = TextSearchEngineClient.get_instance()

    for ds_id in item_ids_by_dataset:
        dataset = get_dataset(ds_id)
        if not any(converter for converter in dataset.applicable_export_converters if converter.identifier == export_converter_identifier):
            continue

        if "__all__" in required_fields:
            required_fields = dataset.object_fields.keys()

        items = search_engine_client.get_items_by_ids(dataset, item_ids_by_dataset[ds_id], fields=required_fields)
        all_items.extend(items)

    exported_data = converter.export_multiple(all_items)
    return exported_data


class ExportConverter():

    def __init__(self, params: dict):
        self.params = params

    def required_fields(self) -> tuple:
        return ("__all__",)

    def export_single(self, item: DotDict) -> dict:
        raise NotImplementedError

    def export_multiple(self, items: Iterable[dict]) -> dict:
        raise NotImplementedError


def get_export_converter_module(name: str, params: dict) -> ExportConverter:
    converters = {
        "bibtex": BibtexExport,
        "apa": ApaExport,
        "ris": RisExport,
    }
    if name in converters:
        return converters[name](params)
    raise ValueError(f"export converter {name} not found")


class BibtexExport(ExportConverter):
    def required_fields(self) -> tuple:
        return ("title", "authors", "publication_year")

    def export_single(self, item: DotDict) -> dict:
        first_author = item.authors.split(" ")[0] if item.authors else ""
        if not first_author:
            first_author = "_".join(item.title.lower().split(" "))[:10]
        if item.publication_year:
            cite_key = f'{first_author}_{item.publication_year}'
        else:
            cite_key = first_author
        value = f"""@article{{
    {cite_key},
    title="{item.title}",
    author="{item.authors}",
    year={item.publication_year if item.publication_year else "n.d."},
}}"""
        return { "value": value, "filename": "citation.bib" }

    def export_multiple(self, items: Iterable[dict]) -> dict:
        values = [self.export_single(DotDict(item))["value"] for item in items]
        content = "\n\n".join(values)
        return { "value": content, "filename": "citations.bib" }


class ApaExport(ExportConverter):
    def required_fields(self) -> tuple:
        return ("title", "authors", "publication_year")

    def export_single(self, item: DotDict) -> dict:
        value = f"""{item.authors} ({item.publication_year}). {item.title}."""
        return { "value": value, "filename": "citation.txt" }


class RisExport(ExportConverter):
    def required_fields(self) -> tuple:
        return ("title", "authors", "publication_year")

    def export_single(self, item: DotDict) -> dict:
        value = f"""TY  - JOUR
AU  - {item.authors}
PY  - {item.publication_year}
TI  - {item.title}"""
        return { "value": value, "filename": "citation.ris" }

