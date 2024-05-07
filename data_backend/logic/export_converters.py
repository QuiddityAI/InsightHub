from utils.dotdict import DotDict

from database_client.django_client import get_dataset, get_export_converter

from logic.search_common import get_document_details_by_id


def export_item(dataset_id: int, item_id: int, export_converter_identifier: str) -> dict:
    import_converter = get_export_converter(export_converter_identifier)
    converter = get_export_converter_module(import_converter.module, import_converter.parameters)
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


class ExportConverter():

    def __init__(self, params: dict):
        self.params = params

    def required_fields(self) -> tuple:
        return ("__all__",)

    def export_single(self, item: DotDict) -> dict:
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

