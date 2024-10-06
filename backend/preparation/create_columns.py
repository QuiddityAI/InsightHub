from data_map_backend.models import DataCollection, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType
from .prompts import item_relevancy_prompt


def create_relevance_column(collection: DataCollection, query: str) -> CollectionColumn:
    column = CollectionColumn(
        collection=collection,
        name="Relevance",
        identifier="relevance"
    )
    column.field_type = FieldType.ARBITRARY_OBJECT
    column.expression = f"How is this item relevant to the query '{query}'?"
    # replace expression already here to be able to use a more descriptive expression above to be display in the UI
    column.prompt_template = item_relevancy_prompt.replace("{{ expression }}", query)
    column.source_fields = [COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS]
    column.module = 'groq_llama_3_70b'
    column.auto_run_for_candidates = True
    column.determines_relevance = True
    column.save()
    return column
