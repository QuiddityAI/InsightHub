import base64
import json
import logging
import os
import re
from typing import Dict, List, Type, TypeVar

import json_repair
import litellm
from pydantic import ValidationError

from litellmonkey.config import (
    get_all_model_configs,
    get_litellm_kwargs,
    get_litellm_model,
    get_model_config,
    resolve_alias,
)
from litellmonkey.models import (
    ChatResponse,
    EmbeddingResponse,
    ModelConfig,
    PromptMessage,
    RerankItem,
    RerankResponse,
    TokenUsage,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _count_tokens_rough(text: str) -> int:
    tokens = re.split(r"\s+|[()\[\]{}.,:;+=*/\\\"\'<>-]", text)
    return len([t for t in tokens if t])


class LiteLLModel:
    def __init__(self, model_id: str, api_key: str = ""):
        self._original_id = model_id
        self._canonical_id = resolve_alias(model_id)
        self._litellm_model = get_litellm_model(model_id)
        self._config = get_model_config(model_id)
        self._litellm_kwargs = get_litellm_kwargs(model_id)
        if api_key:
            self._litellm_kwargs["api_key"] = api_key

    @property
    def model_id(self) -> str:
        """Returns the ID used to construct this model (may be alias or canonical)."""
        return self._original_id

    @property
    def canonical_id(self) -> str:
        """Returns the canonical model ID (the YAML key)."""
        return self._canonical_id

    @property
    def config(self) -> ModelConfig:
        return self._config

    @classmethod
    def load(cls, model_id: str, **kwargs) -> "LiteLLModel":
        return cls(model_id, **kwargs)

    @classmethod
    def available_models(cls) -> Dict[str, "LiteLLModel"]:
        configs = get_all_model_configs()
        return {cid: cls(cid) for cid in configs}

    @classmethod
    def available_model_configs(cls) -> dict:
        configs = get_all_model_configs()
        result = {}
        for cid, cfg in configs.items():
            dumped = cfg.model_dump(mode="json")
            dumped["provider"] = cid.split("/")[0]
            result[cid] = dumped
        return result

    def _validate_input(self, conversation: List[PromptMessage]) -> None:
        total_tokens = sum(_count_tokens_rough(msg.content) for msg in conversation)
        if total_tokens > self._config.max_input_tokens:
            raise ValueError(
                f"Input tokens (~{total_tokens}) exceed the maximum limit of {self._config.max_input_tokens}."
            )

    def _build_messages(self, conversation: List[PromptMessage]) -> list[dict]:
        messages = []
        for msg in conversation:
            if msg.role in ("system", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})
            else:  # user
                if msg.image:
                    content = [{"type": "text", "text": msg.content}]
                    if isinstance(msg.image, str):
                        content.append({"type": "image_url", "image_url": {"url": msg.image}})
                    elif isinstance(msg.image, bytes):
                        b64 = base64.b64encode(msg.image).decode("utf-8")
                        content.append(
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        )
                    messages.append({"role": "user", "content": content})
                else:
                    messages.append({"role": "user", "content": msg.content})
        return messages

    def _calculate_cost(self, response=None, token_usage: TokenUsage = None) -> float | None:
        """Calculate cost using litellm if response available, else fallback to config prices."""
        if response is not None:
            try:
                cost = litellm.completion_cost(response)
                if cost and cost > 0:
                    return cost
            except Exception:
                pass
        # Fallback: manual calculation from config
        if token_usage and token_usage.prompt_tokens and token_usage.completion_tokens:
            cost = token_usage.prompt_tokens / 1e6 * self._config.usd_per_1M_input_tokens
            cost += token_usage.completion_tokens / 1e6 * self._config.usd_per_1M_output_tokens
            return cost
        if token_usage and token_usage.total_tokens:
            av_price = (self._config.usd_per_1M_input_tokens + self._config.usd_per_1M_output_tokens) / 2
            return token_usage.total_tokens / 1e6 * av_price
        return None

    def generate_prompt_response(
        self,
        user_prompt: str = "",
        system_prompt: str = "",
        image=None,
        temperature=0.7,
        max_tokens=None,
        api_key: str = "",
    ) -> ChatResponse:
        conversation = []
        if system_prompt:
            conversation.append(PromptMessage(role="system", content=system_prompt))
        if user_prompt:
            conversation.append(PromptMessage(role="user", content=user_prompt, image=image))
        return self.generate_chat_response(conversation, temperature, max_tokens, api_key)

    def generate_chat_response(
        self,
        conversation: List[PromptMessage] = None,
        temperature=0.7,
        max_tokens=None,
        api_key: str = "",
    ) -> ChatResponse:
        conversation = conversation or []
        self._validate_input(conversation)
        messages = self._build_messages(conversation)

        kwargs = {
            "model": self._litellm_model,
            "messages": messages,
            "temperature": temperature,
            **self._litellm_kwargs,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if api_key:
            kwargs["api_key"] = api_key

        response = litellm.completion(**kwargs)

        assistant_msg = response.choices[0].message.content
        token_usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )
        token_usage.total_cost = self._calculate_cost(response=response, token_usage=token_usage)

        full_conversation = conversation + [PromptMessage(role="assistant", content=assistant_msg)]

        return ChatResponse(
            provider_used=self._canonical_id.split("/")[0],
            model_used=self._canonical_id,
            token_usage=token_usage,
            conversation=full_conversation,
        )

    def generate_structured_response(
        self,
        data_model: Type[T],
        user_prompt: str = "",
        system_prompt: str = "",
        image=None,
        temperature=0.7,
        max_tokens=None,
    ) -> tuple[T, ChatResponse]:
        retries = 3
        s = ""
        for attempt in range(retries):
            resp = self.generate_prompt_response(user_prompt, system_prompt, image, temperature, max_tokens)
            try:
                s = resp.conversation[-1].content
                data = json_repair.loads(s)
                return data_model.model_validate(data), resp
            except (json.JSONDecodeError, ValidationError, IndexError) as e:
                if attempt == retries - 1:
                    raise ValueError(f"Validation failed after {retries} attempts: {e}. str: {s}")
        raise ValueError(f"Failed after {retries} retries, last str: {s}")

    def generate_structured_array_response(
        self,
        data_model: Type[T],
        user_prompt: str = "",
        system_prompt: str = "",
        image=None,
        temperature=0.7,
        max_tokens=None,
        as_dicts=False,
    ) -> tuple[list, ChatResponse]:
        retries = 3
        s = ""
        for attempt in range(retries):
            resp = self.generate_prompt_response(user_prompt, system_prompt, image, temperature, max_tokens)
            try:
                s = resp.conversation[-1].content
                array_of_dicts = json_repair.loads(s)
                if array_of_dicts == "":
                    raise ValueError(f"Can't parse JSON: {s}")
                if not isinstance(array_of_dicts, list):
                    raise ValueError(f"Expected a list, got {type(array_of_dicts)}")
                array_of_models = [data_model(**d) for d in array_of_dicts]
                if as_dicts:
                    return [m.model_dump() for m in array_of_models], resp
                return array_of_models, resp
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"Failed to parse JSON: {e}")
                    raise ValueError(f"Validation failed after {retries} attempts: {e}. str: {s}")
        raise ValueError(f"Failed after {retries} retries, last str: {s}")

    def generate_short_text(
        self,
        user_prompt: str = "",
        system_prompt: str = "",
        image=None,
        temperature=0.7,
        max_tokens=None,
        api_key: str = "",
        exact_required_length: int | None = None,
        strip_output: bool = True,
        retries: int = 3,
    ) -> str | None:
        text: str | None = None
        while not text and retries > 0:
            retries -= 1
            response = self.generate_prompt_response(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                image=image,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )
            text = response.conversation[-1].content
            if strip_output:
                text = text.strip().strip("```").strip('"').strip("'").strip()
            if exact_required_length and len(text) != exact_required_length:
                text = None
        return text

    def generate_embeddings(self, text: str = "") -> EmbeddingResponse:
        tokens = _count_tokens_rough(text)
        if tokens > self._config.max_input_tokens:
            raise ValueError(f"Input tokens exceed maximum limit of {self._config.max_input_tokens}.")

        response = litellm.embedding(
            model=self._litellm_model, input=[text], **self._litellm_kwargs
        )

        token_usage = TokenUsage(
            total_tokens=response.usage.total_tokens if response.usage else None,
        )
        token_usage.total_cost = self._calculate_cost(response=response, token_usage=token_usage)

        return EmbeddingResponse(
            provider_used=self._canonical_id.split("/")[0],
            model_used=self._canonical_id,
            token_usage=token_usage,
            embedding=response.data[0]["embedding"],
        )

    def rerank(
        self,
        query: str = "",
        documents: list = None,
        top_n: int = 3,
        rank_fields: list = None,
        api_key: str = "",
    ) -> RerankResponse:
        import cohere

        api_key = api_key or self._litellm_kwargs.get("api_key") or os.environ.get("COHERE_API_KEY", "")
        client = cohere.Client(api_key)
        # Strip provider prefix from model name for Cohere API
        model_name = self._config.identifier.split("/")[-1] if "/" in self._config.identifier else self._config.identifier
        resp = client.rerank(
            model=model_name,
            query=query,
            documents=documents or [],
            top_n=top_n,
            rank_fields=rank_fields if rank_fields else None,
        )
        return RerankResponse(
            provider_used="cohere",
            model_used=self._canonical_id,
            token_usage=TokenUsage(search_units=resp.meta.billed_units.search_units),
            reranked_documents=[
                RerankItem(index=item.index, score=item.relevance_score) for item in resp.results
            ],
        )

    def to_litellm(self) -> dict:
        """Returns kwargs dict compatible with litellm.completion() and dspy.LM()."""
        return {"model": self._litellm_model, **self._litellm_kwargs}
