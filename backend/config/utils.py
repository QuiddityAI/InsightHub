import dspy
from llmonkey.llms import BaseLLMModel
from .llm import default_dspy_models, default_models
from typing import Literal, Type


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
        llmonkey_model = BaseLLMModel.load(default_dspy_models[task_name])
    except KeyError:
        raise ValueError(f"Default model not found for signature {task_name}")
    return llmonkey_model
