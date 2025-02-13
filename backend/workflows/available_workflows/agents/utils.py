from dspy.dsp.utils.settings import settings as dspy_settings
import dspy


def override_dspy_model(**kwargs):
    lm = dspy_settings.config["lm"]
    current_kwargs = lm.kwargs.copy()
    current_kwargs.update(kwargs)
    return dspy.LM(lm.model, **current_kwargs)
