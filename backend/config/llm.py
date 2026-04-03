import box

from litellmonkey.config import get_defaults

default_models = box.Box(get_defaults("models"))
default_dspy_models = box.Box(get_defaults("dspy"))
default_pdferret_models = box.Box(get_defaults("pdferret"))
