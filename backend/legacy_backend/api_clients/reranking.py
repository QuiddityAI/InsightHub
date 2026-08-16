import logging

from config.llm import default_rerank_model
from litellmonkey.llm import LiteLLModel
from litellmonkey.models import RerankItem, RerankResponse, TokenUsage

logger = logging.getLogger(__name__)


def get_reranking_results(
    query: str, texts: tuple[str, ...], top_n: int = 10, model: str | None = None
) -> RerankResponse:
    """Rerank `texts` by relevance to `query` using the configured rerank model.

    The model is configured in backend/config/llm_models.yaml (defaults.rerank.default).
    On failure the original order is returned (with zero scores), so that callers
    degrade to the un-reranked ranking instead of failing.
    """
    model = model or default_rerank_model
    try:
        return LiteLLModel(model).rerank(query=query, documents=list(texts), top_n=top_n)
    except Exception as e:
        logger.error(f"Failed to rerank query: {query} with model {model} and error: {e}")
        return RerankResponse(
            provider_used=model.split("/")[0],
            model_used=model,
            token_usage=TokenUsage(),
            reranked_documents=[RerankItem(index=i, score=0.0) for i in range(min(len(texts), top_n))],
        )
