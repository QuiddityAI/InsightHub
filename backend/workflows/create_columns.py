from llmonkey.llms import Google_Gemini_Flash_1_5_v1

from data_map_backend.models import DataCollection, CollectionColumn, COLUMN_META_SOURCE_FIELDS, FieldType, User
from workflows.prompts import criteria_prompt


def create_relevance_column(collection: DataCollection, query: str, language: str | None, user: User) -> CollectionColumn:
    prompt = criteria_prompt[language or 'en'].replace("{{ query }}", query)
    default_criteria = "- is relevant to the query '{{ query }}'".replace("{{ query }}", query)
    criteria_list = Google_Gemini_Flash_1_5_v1().generate_short_text(prompt) or default_criteria

    column = CollectionColumn(
        collection=collection,
        name="Relevance",
        identifier="relevance",
        field_type=FieldType.ARBITRARY_OBJECT,
        expression=criteria_list,
        prompt_template=None,
        source_fields=[COLUMN_META_SOURCE_FIELDS.DESCRIPTIVE_TEXT_FIELDS, COLUMN_META_SOURCE_FIELDS.FULL_TEXT_SNIPPETS],
        module='relevance',
        parameters={
            'model': user.preferences.get("default_small_llm") or Google_Gemini_Flash_1_5_v1.__name__,
            'language': language
        },
        auto_run_for_candidates=True,
    )
    column.save()
    return column

