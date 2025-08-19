from typing import Literal, Type, Union

import dspy
from llmonkey.llms import BaseLLMModel

from config.llm import default_dspy_models, default_models


def get_default_model(size: Literal["small", "medium", "large"]) -> BaseLLMModel:
    """
    Retrieve the default language model (LM) for a given size.
    Args:
        size (str): The size of the model to retrieve.

    """
    return BaseLLMModel.load(default_models[size])


def get_default_dspy_llm_kwargs(task_name: str) -> Union[dict]:
    """
    Retrieve the default language model (LM) for the given task.

    """
    model_params = default_dspy_models.get(task_name)
    if model_params is None:
        raise ValueError(f"Default model not found for signature {task_name}")

    if isinstance(model_params, str):
        try:
            return BaseLLMModel.load(model_params).to_litellm()
        except Exception as e:
            raise RuntimeError(f"Failed to load model '{model_params}' for task '{task_name}': {e}")
    elif isinstance(model_params, dict):
        return model_params
    else:
        raise TypeError(f"Model params for task '{task_name}' must be a string or dict, got {type(model_params)}")
