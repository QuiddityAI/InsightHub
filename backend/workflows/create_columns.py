from llmonkey.llms import Mistral_Mistral_Small

from data_map_backend.models import DataCollection, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType


def create_relevance_column(collection: DataCollection, criteria: str, language: str | None) -> CollectionColumn:
    column = CollectionColumn(
        collection=collection,
        name="Relevance",
        identifier="relevance",
        field_type=FieldType.ARBITRARY_OBJECT,
        expression=criteria,
        prompt_template=None,
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS, COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS],
        module='relevance',
        parameters={'model': Mistral_Mistral_Small.__name__, language: language},
        auto_run_for_candidates=True,
        determines_relevance=True,
    )
    column.save()
    return column

