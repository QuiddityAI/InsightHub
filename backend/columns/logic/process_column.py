import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from django.db.models.manager import BaseManager
from django.utils import timezone

from columns.logic.llm_column import generate_llm_cell_data
from columns.logic.web_search_column import google_search
from columns.logic.website_scraping_column import scrape_website_module
from columns.schemas import CellData, ColumnCellRange
from data_map_backend.models import (
    CollectionColumn,
    CollectionItem,
    DataCollection,
    FieldType,
)
from legacy_backend.logic.chat_and_extraction import get_item_question_context
from legacy_backend.logic.search_common import get_document_details_by_id


def remove_column_data_from_collection_items(collection_items: Iterable[CollectionItem], column_identifier: str):
    items_to_save = []
    for item in collection_items:
        if item.column_data and column_identifier in item.column_data:
            del item.column_data[column_identifier]
            items_to_save.append(item)
    if items_to_save:
        CollectionItem.objects.bulk_update(items_to_save, ["column_data"])


def get_collection_items_from_cell_range(column: CollectionColumn, cell_range: ColumnCellRange):
    if cell_range.collection_item_id:
        collection_items = CollectionItem.objects.filter(id=cell_range.collection_item_id)
    else:
        collection_items = CollectionItem.objects.filter(collection=column.collection)
        collection_items = collection_items.order_by(cell_range.order_by)
        collection_items = (
            collection_items[cell_range.offset : cell_range.offset + cell_range.limit]
            if cell_range.limit > 0
            else collection_items[cell_range.offset :]
        )
    return collection_items


def process_cells_blocking(
    collection_items: BaseManager[CollectionItem] | list[CollectionItem],
    column: CollectionColumn,
    collection: DataCollection,
    user_id: int,
):
    assert isinstance(collection.columns_with_running_processes, list)
    collection.columns_with_running_processes.append(column.identifier)
    collection.save(update_fields=["columns_with_running_processes"])

    batch_size = 10
    try:
        for i in range(0, len(collection_items), batch_size):
            batch = collection_items[i : i + batch_size]
            _process_cell_batch(batch, column, collection, user_id)
        logging.warning("Done extracting question from collection class items.")
    except Exception as e:
        logging.error(e)
        import traceback

        logging.error(traceback.format_exc())
    finally:
        collection.columns_with_running_processes.remove(column.identifier)
        collection.save(update_fields=["columns_with_running_processes"])


def _process_cell_batch(
    collection_items: BaseManager[CollectionItem] | list[CollectionItem],
    column: CollectionColumn,
    collection: DataCollection,
    user_id: int,
):
    if not column.module:
        logging.warning(f"No module specified for column {column.identifier}.")
        return

    data_item_source_fields = [name for name in column.source_fields if not name.startswith("_")]
    source_column_identifiers = [
        name.replace("_column__", "") for name in column.source_fields if name.startswith("_column__")
    ]
    source_columns = CollectionColumn.objects.filter(collection=collection, identifier__in=source_column_identifiers)

    module_definitions = {
        "llm": {"input_type": "natural_language"},
        "relevance": {"input_type": "natural_language"},
        "python_expression": {"input_type": "json"},
        "web_search": {"input_type": "json"},
        "item_field": {"input_type": "json"},
        "notes": {"input_type": None},
        "website_scraping": {"input_type": "json"},
        "email": {"input_type": "json"},
    }
    if column.module not in module_definitions:
        logging.warning(f"Column Processing: Module {column.module} not found.")
        return
    input_type = module_definitions[column.module]["input_type"]

    def process_cell(collection_item: CollectionItem):
        if (collection_item.column_data or {}).get(column.identifier, {}).get("value"):
            # already extracted (only empty fields are extracted again)
            return

        input_data = None
        if collection_item.field_type == FieldType.TEXT:
            # the collection item is not a reference to a database item, but just a string:
            input_data = json.dumps({"_id": collection_item.id, "text": collection_item.value}, indent=2)
        elif collection_item.field_type == FieldType.IDENTIFIER:
            assert collection_item.dataset_id is not None
            assert collection_item.item_id is not None
            if input_type == "natural_language":
                input_data = get_item_question_context(
                    collection_item.dataset_id, collection_item.item_id, column.source_fields, column.expression or ""
                )["context"]
                for additional_source_column in source_columns:
                    if not collection_item.column_data:
                        continue
                    column_data = collection_item.column_data.get(additional_source_column.identifier)
                    if column_data and column_data.get("value"):
                        input_data += f"\n{additional_source_column.name}: {column_data['value']}"
            elif input_type == "json":
                input_data = get_document_details_by_id(
                    collection_item.dataset_id, collection_item.item_id, tuple(data_item_source_fields)
                )
                assert input_data is not None
                for additional_source_column in source_columns:
                    if not collection_item.column_data:
                        continue
                    column_data = collection_item.column_data.get(additional_source_column.identifier)
                    if column_data and column_data.get("value"):
                        input_data["_column__" + additional_source_column.identifier] = column_data["value"]
        else:
            logging.warning(
                f"Column Processing: Unknown field type {collection_item.field_type} for item {collection_item.id}."
            )

        if not input_data:
            logging.warning(f"Column Processing: Could not extract input dat for item {collection_item.id}.")
            return

        module = column.module

        cell_data: CellData = CellData(
            changed_at=timezone.now().isoformat(),
        )

        if module == "python_expression":
            cell_data.value = "Not implemented"
            cell_data.is_computed = True
        elif module == "website_scraping":
            cell_data = scrape_website_module(input_data, column.source_fields)
        elif module == "web_search":
            cell_data = google_search(input_data, column.source_fields)
        elif module == "llm":
            assert isinstance(input_data, str)
            cell_data = generate_llm_cell_data(input_data, column, user_id)
        elif module == "relevance":
            assert isinstance(input_data, str)
            cell_data = generate_llm_cell_data(input_data, column, user_id, is_relevance_column=True)
        elif module == "item_field":
            assert isinstance(input_data, dict)
            cell_data.value = input_data.get(column.source_fields[0]) or "-"
            cell_data.is_computed = True
        else:
            cell_data.value = "Module not found"
            cell_data.is_computed = True

        if collection_item.column_data is None:
            collection_item.column_data = {}
        collection_item.column_data[column.identifier] = cell_data.dict()
        collection_item.save(update_fields=["column_data"])

    def process_cell_safe(collection_item: CollectionItem):
        try:
            process_cell(collection_item)
        except Exception as e:
            logging.error(f"Error processing cell {collection_item.id}: {e}")
            import traceback

            logging.error(traceback.format_exc())
            try:
                cell_data = CellData(
                    value=f"Error processing cell: {e}",
                    changed_at=timezone.now().isoformat(),
                )
                collection_item.column_data[column.identifier] = cell_data.dict()
                collection_item.save(update_fields=["column_data"])
            except Exception as e:
                logging.error(f"Error saving error message for cell {collection_item.id}: {e}")
                import traceback

                logging.error(traceback.format_exc())

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_cell_safe, collection_items)
