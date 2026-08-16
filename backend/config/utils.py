from typing import Any, Literal, Type

import dspy
from litellmonkey import BaseLLMModel

from config.llm import default_dspy_models, default_fallback_chain, default_models


def get_default_model(size: Literal["small", "medium", "large"]) -> BaseLLMModel:
    """
    Retrieve the default language model (LM) for a given size.
    Args:
        size (str): The size of the model to retrieve.

    """
    return BaseLLMModel.load(default_models[size])


def get_default_dspy_llm(task_name: str) -> BaseLLMModel:
    """
    Retrieve the default language model (LM) for the given task.

    """
    try:
        model = BaseLLMModel.load(default_dspy_models[task_name])
    except KeyError:
        raise ValueError(f"Default model not found for signature {task_name}")
    return model


def get_dspy_fallback_chain() -> list[BaseLLMModel]:
    """Return the list of fallback models loaded from the config fallback_chain."""
    return [BaseLLMModel.load(model_id) for model_id in default_fallback_chain]


def dspy_call_with_fallback(
    predictor: Any,
    primary_model: BaseLLMModel,
    lm_kwargs: dict | None = None,
    **predictor_kwargs: Any,
) -> Any:
    """
    Call a dspy predictor (Predict singleton or Module instance) with automatic
    fallback through the global fallback_chain on failure.

    Args:
        predictor: A callable dspy predictor (dspy.Predict instance or dspy.Module instance).
        primary_model: The primary BaseLLMModel to use first.
        lm_kwargs: Optional extra kwargs forwarded to dspy.LM() (e.g. max_tokens, temperature).
        **predictor_kwargs: Keyword arguments passed to the predictor.

    Returns:
        The result of the first successful predictor call.

    Raises:
        The last exception if every model in the chain fails.
    """
    import logging

    extra_lm_kwargs = lm_kwargs or {}
    models = [primary_model] + get_dspy_fallback_chain()
    last_exc: Exception | None = None
    for model in models:
        try:
            with dspy.context(lm=dspy.LM(**model.to_litellm(), **extra_lm_kwargs)):
                return predictor(**predictor_kwargs)
        except Exception as exc:
            logging.warning(
                f"dspy_call_with_fallback: model '{model.model_id}' failed "
                f"({type(exc).__name__}: {exc}). Trying next in chain..."
            )
            last_exc = exc
    raise last_exc  # type: ignore[misc]
