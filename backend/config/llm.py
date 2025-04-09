import box

default_models = box.Box(
    {
        "small": "Mistral_Ministral8b",
        "medium": "Mistral_Mistral_Large",
        "large": "Mistral_Mistral_Large",
    }
)


default_dspy_models = box.Box(
    {
        "column_title": "Mistral_Ministral8b",
        "column_language": "Mistral_Ministral3b",
        "query_language": "Mistral_Ministral3b",
        "doc_comparison": "Mistral_Mistral_Large",
        "search_query": "Mistral_Mistral_Small",
        "tender_summary": "Mistral_Mistral_Small",
    }
)

default_pdferret_models = box.Box(
    {
        "vision": "Mistral_Mistral_Small",
        "text": "Mistral_Pixtral",
    }
)
