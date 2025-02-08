import box

default_models = box.Box(
    {
        "small": "Mistral_Ministral8b",
        "medium": "Google_Gemini_Flash_1_5_v1",
        "large": "Google_Gemini_Flash_1_5_v1",  # TODO: Find a better model instead of Nebius
    }
)


default_dspy_models = box.Box(
    {
        "column_title": "Mistral_Ministral8b",
        "column_language": "Mistral_Ministral3b",
        "query_language": "Mistral_Ministral3b",
        "doc_comparison": "Google_Gemini_Flash_1_5_v1",
        "search_query": "Google_Gemini_Flash_1_5_v1",
        "tender_summary": "Mistrall_Ministral8b",
    }
)

default_pdferret_models = box.Box(
    {
        "vision": "Google_Gemini_Flash_1_5_v1",
        "text": "Google_Gemini_Flash_1_5_v1",
    }
)
