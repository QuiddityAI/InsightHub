import os


default_embedding_provider = "sentence_transformer"

# TODO: intfloat/e5-large-v2 is not available in ollama, need to add it manually
local_embedding_models = {
    "intfloat/e5-base-v2": "ollama/jeffh/intfloat-e5-base-v2:f16",
    "intfloat/multilingual-e5-base": "ollama/yxchia/multilingual-e5-base",
}


def get_local_emb_litellm_kwargs(model: str) -> dict:
    model_str = local_embedding_models.get(model)
    if model_str is None:
        raise ValueError(f"Model {model} not present in ollama")
    api_base = os.getenv("LOCAL_OLLAMA_URL", "http://ollama:11434")
    return dict(model=model_str, api_base=api_base)


def get_hosted_emb_litellm_kwargs(model: str) -> dict:
    kwargs = dict(
        model=f"openai/{model}",
        api_base="https://api.deepinfra.com/v1/openai",
        encoding_format="float",
        api_key=os.environ.get("DEEPINFRA_API_KEY", "no_api_key"),
    )
    return kwargs


VERTEX_PROJECT_ID = "visual-data-map"
VERTEX_LOCATION = "europe-west3"

clip_model_kwargs = dict(
    model="vertex_ai/multimodalembedding@001",
    vertex_ai_project=VERTEX_PROJECT_ID,
    vertex_ai_location=VERTEX_LOCATION,
)
