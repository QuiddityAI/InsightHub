import box

from litellmonkey.config import get_defaults, get_defaults_list

default_models = box.Box(get_defaults("models"))
default_dspy_models = box.Box(get_defaults("dspy"))
default_pdferret_models = box.Box(get_defaults("pdferret"))
default_fallback_chain: list[str] = get_defaults_list("fallback_chain")
