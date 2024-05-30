import io
import json
import logging
from typing import Iterable
import csv

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
        required_fields = tuple(dataset.schema.object_fields.keys())
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

    items, collection_entries = _get_exportable_collection_items(collection_id, class_name,
                                                 converter_definition, required_fields)

    exported_data = converter.export_multiple(items)
    return exported_data


def export_collection_table(collection_id: int, class_name: str,
                            export_converter_identifier: str, format_identifier: str) -> dict:
    converter_definition = get_export_converter(export_converter_identifier)
    converter = get_export_converter_module(converter_definition.module, converter_definition.parameters)
    required_fields = converter.required_fields()

    collection = get_collection(collection_id)
    if not collection:
        return { "value": None, "error": "Collection not found"}

    items, collection_entries = _get_exportable_collection_items(collection_id, class_name,
                                                 converter_definition, required_fields)

    export_format = get_table_export_format(format_identifier)
    exported_data = export_format.export(collection, items, collection_entries, converter)
    return exported_data


def _get_exportable_collection_items(collection_id: int, class_name: str,
                                     converter_definition: DotDict, required_fields: tuple[str]) -> tuple[list, list]:
    collection_items = get_collection_items(collection_id, class_name,
                                            field_type=FieldType.IDENTIFIER, is_positive=True, include_column_data=True)
    collection_items_per_dataset = {}
    for i, collection_item in enumerate(collection_items):
        if collection_item['field_type'] != FieldType.IDENTIFIER:
            continue
        dataset_id = collection_item['dataset_id']
        if dataset_id not in collection_items_per_dataset:
            collection_items_per_dataset[dataset_id] = []
        collection_items_per_dataset[dataset_id].append(collection_item)

    all_items = []
    all_collection_items = []
    search_engine_client = TextSearchEngineClient.get_instance()

    for ds_id in collection_items_per_dataset:
        dataset = get_dataset(ds_id)
        if not converter_definition.universally_applicable and \
            not any(converter for converter in dataset.schema.applicable_export_converters
                   if converter.identifier == converter_definition.identifier):
            continue

        if "__all__" in required_fields:
            required_fields = dataset.schema.object_fields.keys()

        item_ids = [collection_item['item_id'] for collection_item in collection_items_per_dataset[ds_id]]
        items = search_engine_client.get_items_by_ids(dataset, item_ids, fields=required_fields)
        all_items.extend(items)
        all_collection_items.extend(collection_items_per_dataset[ds_id])
    return all_items, all_collection_items


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
        "internal_id": InternalIdExport,
        "json": JsonExport,
        "csv": CSVExport,
        "bibtex": BibtexExport,
        "apa": ApaExport,
        "ris": RisExport,
    }
    if name in converters:
        return converters[name](params)
    raise ValueError(f"export converter {name} not found")


class InternalIdExport(ExportConverter):
    def required_fields(self) -> tuple:
        return tuple()

    def export_single(self, item: DotDict) -> dict:
        value = str([item._dataset_id, item._id])
        return { "value": value, "filename": "internal_id.txt" }

    def export_multiple(self, items: Iterable[dict]) -> dict:
        values = [str([item['_dataset_id'], item['_id']]) for item in items]
        content = "\n".join([str(value) for value in values])
        return { "value": content, "filename": "internal_ids.txt" }


class JsonExport(ExportConverter):
    def required_fields(self) -> tuple:
        return tuple(self.params.get("fields", ['__all__']))

    def export_single(self, item: DotDict) -> dict:
        # the 'include_vector' parameter is ignored for now, vectors are currently never
        # included in the export (because only the text database is queried, not the vector database)
        if "__all__" in self.required_fields():
            value = json.dumps(item, indent=2)
        else:
            value = json.dumps({field: item[field] for field in self.required_fields()}, indent=2)
        return { "value": value, "filename": "item.json" }

    def export_multiple(self, items: Iterable[dict]) -> dict:
        if "__all__" in self.required_fields():
            value = json.dumps(items, indent=2)
        else:
            value = json.dumps([{field: item[field] for field in self.required_fields()} for item in items], indent=2)
        return { "value": value, "filename": "items.json" }


class CSVExport(ExportConverter):
    def required_fields(self) -> tuple:
        return tuple(self.params.get("fields", ['__all__']))

    def export_single(self, item: DotDict) -> dict:
        # the 'include_vector' parameter is ignored for now, vectors are currently never
        # included in the export (because only the text database is queried, not the vector database)
        buffer = io.StringIO()
        csv_writer = csv.writer(buffer)
        if "__all__" in self.required_fields():
            header = item.keys()
            csv_writer.writerow(header)
            csv_writer.writerow([item[field] for field in header])
        else:
            header = self.required_fields()
            csv_writer.writerow(header)
            csv_writer.writerow([item[field] for field in header])
        return { "value": buffer.getvalue(), "filename": "item.csv" }

    def export_multiple(self, items: Iterable[dict]) -> dict:
        buffer = io.StringIO()
        csv_writer = csv.writer(buffer)
        if "__all__" in self.required_fields():
            header = next(iter(items)).keys()
            csv_writer.writerow(header)
            for item in items:
                csv_writer.writerow([item[field] for field in header])
        else:
            header = self.required_fields()
            csv_writer.writerow(header)
            for item in items:
                csv_writer.writerow([item[field] for field in header])
        return { "value": buffer.getvalue(), "filename": "items.csv" }


class BibtexExport(ExportConverter):
    def required_fields(self) -> tuple:
        return ("title", "authors", "publication_year")

    def export_single(self, item: DotDict) -> dict:
        if isinstance(item.authors, list):
            item.authors = "; ".join(item.authors)
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
        if isinstance(item.authors, list):
            item.authors = "; ".join(item.authors)
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


class TableExportFormat():

    def export(self, collection: DotDict, items: list, collection_entries: list,
               converter: ExportConverter) -> dict:
        raise NotImplementedError

    def _get_rows(self, collection: DotDict, items: list, collection_entries: list,
               converter: ExportConverter) -> tuple[list, list]:
        header = ["item_reference", *[column["name"] for column in collection.columns]]
        rows = []
        for item, collection_entry in zip(items, collection_entries):
            row = []
            item_data = converter.export_single(DotDict(item))
            row.append(item_data["value"])
            for column in collection.columns:
                value = collection_entry.get("column_data", {}).get(column["identifier"], {}).get("value", "")
                row.append(value)
            rows.append(row)
        return header, rows


def get_table_export_format(name: str) -> TableExportFormat:
    converters = {
        "xlsx": XlsxTableFormat,
        "csv": CsvTableFormat,
        "json": JsonTableFormat,
    }
    if name in converters:
        return converters[name]()
    raise ValueError(f"export format {name} not found")


class XlsxTableFormat(TableExportFormat):

    def export(self, collection: DotDict, items: list, collection_entries: list,
               converter: ExportConverter) -> dict:
        return {}


class CsvTableFormat(TableExportFormat):

    def export(self, collection: DotDict, items: list, collection_entries: list,
               converter: ExportConverter) -> dict:
        header, rows = self._get_rows(collection, items, collection_entries, converter)
        buffer = io.StringIO()
        csv_writer = csv.writer(buffer)
        csv_writer.writerow(header)
        for row in rows:
            csv_writer.writerow(row)
        return { "value": buffer.getvalue(), "filename": "table.csv" }


class JsonTableFormat(TableExportFormat):

    def export(self, collection: DotDict, items: list, collection_entries: list,
               converter: ExportConverter) -> dict:
        return {}

