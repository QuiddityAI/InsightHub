from litellmonkey.llm import LiteLLModel
from litellmonkey.models import (
    ChatResponse,
    EmbeddingResponse,
    ModelCapabilities,
    ModelConfig,
    ModelLocation,
    PromptMessage,
    RerankItem,
    RerankResponse,
    TokenUsage,
)

# Backward-compatible alias
BaseLLMModel = LiteLLModel

__all__ = [
    "LiteLLModel",
    "BaseLLMModel",
    "ChatResponse",
    "EmbeddingResponse",
    "ModelCapabilities",
    "ModelConfig",
    "ModelLocation",
    "PromptMessage",
    "RerankItem",
    "RerankResponse",
    "TokenUsage",
]
