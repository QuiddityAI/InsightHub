import dspy
from llmonkey.llms import BaseLLMModel
from .llm import default_signature_models, default_models
from typing import Literal, Type


def get_default_model(size: Literal["small", "medium", "large"]) -> BaseLLMModel:
    """
    Retrieve the default language model (LM) for a given size.
    Args:
        size (str): The size of the model to retrieve.

    """
    return BaseLLMModel.load(default_models[size])


def get_default_dspy_llm(dspy_object: Type[dspy.Signature] | dspy.Module) -> BaseLLMModel:
    """
    Retrieve the default language model (LM) for a given dspy object.
    Args:
        dspy_object (dspy.Signature | dspy.Module): The dspy object for which to retrieve
        the default language model.

    """
    if isinstance(dspy_object, dspy.Module):
        signature_name = dspy_object.signature.__name__
    elif isinstance(dspy_object, type) and issubclass(dspy_object, dspy.Signature):
        signature_name = dspy_object.__name__
    else:
        raise ValueError("dspy_object must be a dspy.Signature or dspy.Module")
    try:
        llmonkey_model = BaseLLMModel.load(default_signature_models[signature_name])
    except KeyError:
        raise ValueError(f"Default model not found for signature {signature_name}")
    return llmonkey_model
