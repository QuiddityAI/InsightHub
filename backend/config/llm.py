import box

default_models = box.Box(
    {
        "small": "Mistral_Ministral8b",
        "medium": "Google_Gemini_Flash_1_5_v1",
        "large": "Google_Gemini_Flash_1_5_v1",  # TODO: Find a better model instead of Nebius
    }
)


default_signature_models = box.Box(
    {
        "TitleSignature": "Mistral_Ministral3b",
        "ColumnLanguageSignature": "Mistral_Ministral3b",
        "QueryLanguageSignature": "Mistral_Ministral3b",
        "DocComparisonSignature": "Google_Gemini_Flash_1_5_v1",
        "SearchQuerySignature": "Google_Gemini_Flash_1_5_v1",
    }
)

default_pdferret_models = box.Box(
    {
        "vision": "Google_Gemini_Flash_1_5_v1",
        "text": "Google_Gemini_Flash_1_5_v1",
    }
)
