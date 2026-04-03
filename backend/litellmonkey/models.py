from enum import Enum
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class PromptMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(
        ..., description="Role of the prompt"
    )
    content: str = Field(..., description="Message content")
    image: Optional[Union[str, bytes]] = Field(None, description="Image URL or raw bytes")


class TokenUsage(BaseModel):
    prompt_tokens: Optional[int] = Field(None, description="Number of tokens used in the prompt")
    completion_tokens: Optional[int] = Field(None, description="Number of tokens used in the completion")
    total_tokens: Optional[int] = Field(None, description="Total number of tokens used")
    search_units: Optional[int] = Field(None, description="Number of search units used")
    total_cost: Optional[float] = Field(None, description="Total price of the request in USD")


class ChatResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    provider_used: str = Field(..., description="Provider used to generate this response")
    model_used: str = Field(..., description="Model used to generate this response")
    token_usage: TokenUsage = Field(..., description="Token usage details")
    conversation: List[PromptMessage] = Field(..., description="Conversation messages")


class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    provider_used: str = Field(..., description="Provider used")
    model_used: str = Field(..., description="Model used")
    token_usage: TokenUsage = Field(..., description="Token usage details")
    embedding: List[float] = Field(..., description="Text embeddings")


class RerankItem(BaseModel):
    index: int = Field(..., description="The index of the reranked document")
    score: float = Field(..., description="The score of the reranked document")


class RerankResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    provider_used: str = Field(..., description="Provider used")
    model_used: str = Field(..., description="Model used")
    token_usage: TokenUsage = Field(..., description="Token usage details")
    reranked_documents: List[RerankItem] = Field(..., description="List of reranked documents")


class ModelCapabilities(str, Enum):
    chat = "chat"
    embeddings = "embeddings"
    rerank = "rerank"
    vision = "vision"


class ModelLocation(str, Enum):
    US = "US"
    EU = "EU"
    CA = "CA"
    OTHER = "OTHER"


class ModelConfig(BaseModel):
    identifier: str = Field(..., description="Canonical model identifier")
    verbose_name: str = Field(..., description="Display name")
    description: str = Field("", description="Description of the model")
    max_input_tokens: int = Field(4096, description="Maximum number of tokens in input")
    usd_per_1M_input_tokens: float = Field(0.0, description="Cost per 1M input tokens in USD")
    usd_per_1M_output_tokens: float = Field(0.0, description="Cost per 1M output tokens in USD")
    capabilities: List[ModelCapabilities] = Field(default_factory=list, description="Model capabilities")
    location: Optional[ModelLocation] = Field(None, description="Model geographical location")
    parameters: Optional[str] = Field(None, description="Model size")
