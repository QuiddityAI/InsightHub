from dspy import Module

dspy_model_registry = {}


def register_dspy_model(cls: type[Module]):
    dspy_model_registry[cls.__name__] = cls
    return cls
