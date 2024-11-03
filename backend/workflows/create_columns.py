from llmonkey.llms import Mistral_Mistral_Small, Mistral_Ministral8b

from data_map_backend.models import DataCollection, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType
from workflows.prompts import criteria_prompt


def create_relevance_column(collection: DataCollection, query: str, language: str | None) -> CollectionColumn:
    prompt = criteria_prompt[language or 'en'].replace("{{ query }}", query)
    default_criteria = "- is relevant to the query '{{ query }}'".replace("{{ query }}", query)
    criteria_list = Mistral_Ministral8b().generate_short_text(prompt) or default_criteria

    column = CollectionColumn(
        collection=collection,
        name="Relevance",
        identifier="relevance",
        field_type=FieldType.ARBITRARY_OBJECT,
        expression=criteria_list,
        prompt_template=None,
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS, COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS],
        module='relevance',
        parameters={'model': Mistral_Mistral_Small.__name__, 'language': language},
        auto_run_for_candidates=True,
    )
    column.save()
    return column

