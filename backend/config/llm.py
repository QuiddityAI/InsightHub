import box

default_models = box.Box(
    {
        "small": "Mistral_Ministral8b",
        "medium": "Mistral_Mistral_Small",
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

# for deepinfra
# 'model': 'openai/openai/gpt-oss-120b',
# 'api_key': os.environ.get("LLMONKEY_DEEPINFRA_API_KEY", ""),
# 'api_base': 'https://api.deepinfra.com/v1/openai',

# {'model': 'openai/mistral-large-latest',
# 'api_key': os.environ.get("LLMONKEY_MISTRAL_API_KEY", ""),
# 'api_base': 'https://api.mistral.ai/v1'}

default_mistral_ocr_models = box.Box(
    {
        "ocr": "mistral-ocr-latest",
        "api_key": os.environ.get("LLMONKEY_MISTRAL_API_KEY", ""),
        "metadata_llm_kwargs": {
            "model": "openai/openai/gpt-oss-120b",
            "temperature": 0.1,
            "max_tokens": 4096,
            "api_key": os.environ.get("LLMONKEY_DEEPINFRA_API_KEY", ""),
            "api_base": "https://api.deepinfra.com/v1/openai",
            "reasoning_effort": "low",
            "allowed_openai_params": ['reasoning_effort']
        },
    }
)
