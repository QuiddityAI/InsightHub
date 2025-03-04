import os

default_embedding_provider = "sentence_transformer"

local_embedding_models = {
    "intfloat/e5-base-v2": "openai/intfloat/e5-base-v2",
    "intfloat/multilingual-e5-base": "openai/intfloat/multilingual-e5-base",
    "intfloat/multilingual-e5-large-instruct": "openai/intfloat/multilingual-e5-large-instruct",
    "allenai/specter2_base": "openai/allenai/specter2_base",
}


def get_local_emb_litellm_kwargs(model: str) -> dict:
    model_str = local_embedding_models.get(model)
    if model_str is None:
        raise ValueError(f"Model {model} not present in infinity")
    api_base = os.getenv("LOCAL_MODEL_SERVER_URL", "http://infinity-model-server:55181")
    return dict(model=model_str, api_base=api_base)


def get_hosted_emb_litellm_kwargs(model: str) -> dict:
    # this model is not available in deepinfra or any other hosted service
    # also, EU hosting problem, we might want to always use local embeddings
    if model == "intfloat/multilingual-e5-large-instruct":
        return get_local_emb_litellm_kwargs(model)
    kwargs = dict(
        model=f"openai/{model}",
        api_base="https://api.deepinfra.com/v1/openai",
        encoding_format="float",
        api_key=os.environ.get("DEEPINFRA_API_KEY", "no_api_key"),
    )
    return kwargs


VERTEX_PROJECT_ID = "visual-data-map"
VERTEX_LOCATION = "europe-west3"

google_multimodal_model_kwargs = dict(
    model="vertex_ai/multimodalembedding@001",
    vertex_ai_project=VERTEX_PROJECT_ID,
    vertex_ai_location=VERTEX_LOCATION,
)
