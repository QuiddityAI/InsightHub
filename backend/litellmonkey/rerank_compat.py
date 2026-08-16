"""Compatibility patches for provider /rerank endpoints litellm can't parse yet.

Fireworks serves a Cohere-style `/v1/rerank` endpoint, but returns the ranking
under an OpenAI-style `data` key instead of Cohere's `results`. litellm has no
fireworks_ai rerank provider at all, so we route Fireworks through its
"infinity" provider (same request format, configurable api_base) and rewrite the
response body before litellm's transformer looks for `results`.

Remove this once litellm ships a native fireworks_ai rerank provider.
"""

import httpx
from litellm.llms.infinity.rerank.transformation import InfinityRerankConfig

_original_transform = InfinityRerankConfig.transform_rerank_response


def _transform_rerank_response(self, model, raw_response, *args, **kwargs):
    try:
        body = raw_response.json()
    except Exception:
        return _original_transform(self, model, raw_response, *args, **kwargs)

    if "results" not in body and isinstance(body.get("data"), list):
        body = {**body, "results": body["data"]}
        raw_response = httpx.Response(
            status_code=raw_response.status_code,
            json=body,
            request=raw_response.request,
        )

    return _original_transform(self, model, raw_response, *args, **kwargs)


_transform_rerank_response._litellmonkey_patched = True


def apply_rerank_compat_patches() -> None:
    """Idempotently install the response patches. Called on import of litellmonkey.llm."""
    if getattr(InfinityRerankConfig.transform_rerank_response, "_litellmonkey_patched", False):
        return
    InfinityRerankConfig.transform_rerank_response = _transform_rerank_response
