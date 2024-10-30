from llmonkey.llms import Mistral_Mistral_Small

from data_map_backend.models import DataCollection, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType
from workflows.prompts import item_relevancy_prompt, item_relevancy_prompt_de


def create_relevance_column(collection: DataCollection, query: str, language: str | None) -> CollectionColumn:
    column = CollectionColumn(
        collection=collection,
        name="Relevance",
        identifier="relevance"
    )
    column.field_type = FieldType.ARBITRARY_OBJECT
    # replace expression already here to be able to use a more descriptive expression above to be display in the UI
    if language == 'de':
        column.expression = f"Wie ist dieses Dokument relevant für die Abfrage '{query}'?"
        column.prompt_template = item_relevancy_prompt_de.replace("{{ expression }}", query)
    else:
        column.expression = f"How is this item relevant to the query '{query}'?"
        column.prompt_template = item_relevancy_prompt.replace("{{ expression }}", query)
    column.source_fields = [COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS]
    column.module = 'llm'
    column.parameters = {'model': Mistral_Mistral_Small.__name__}
    column.auto_run_for_candidates = True
    column.determines_relevance = True
    column.save()
    return column
