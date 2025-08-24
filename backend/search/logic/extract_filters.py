import logging
import re
import json

import dspy
from pydantic import BaseModel

from backend.config.utils import get_default_model
from data_map_backend.models import DataCollection, Dataset
from search.schemas import SearchTaskSettings

# TODO: migrate to DSPy + optimize prompts + re-enable feature

model = get_default_model("medium")

class Filter(BaseModel):
    field: str
    dataset_id: int | None = None
    operator: str
    value: str
    label: str | None = None

def get_filter_prompt(dataset_id: int, language: str):
    dataset = Dataset.objects.get(id=dataset_id)
    dataset_filter_prompt = _get_filter_prompt_for_language(dataset.filter_prompts, language)
    schema_filter_prompt = _get_filter_prompt_for_language(dataset.schema.filter_prompts, language)
    return dataset_filter_prompt or schema_filter_prompt


def _get_filter_prompt_for_language(filter_prompts: str | None, language: str):
    if not filter_prompts:
        return None
    prompts = filter_prompts.split("# language: ")
    for prompt in prompts:
        if not prompt.strip():
            continue
        if prompt.startswith(language):
            return prompt.strip(language).strip()
    logging.warning(f"Failed to find filter prompt for language {language} in {filter_prompts}")
    return None


class ExtractFiltersSignature(dspy.Signature):
    """Given a user prompt, generate a JSON array of filter objects matching the Filter schema.
    """
    user_input: str = dspy.InputField(desc="User input to extract filters from")
    filters: list[Filter] = dspy.OutputField(desc="array of filter objects")


extract_filters_predictor = dspy.Predict(ExtractFiltersSignature)


def extract_filters(search_task: SearchTaskSettings, filter_prompt: str):
    """
    Generate filters using DSPy + the configured LM. Returns a list of dicts or None on failure.
    """
    try:
        with dspy.context(lm=dspy.LM(**model.to_litellm())):
            result = extract_filters_predictor(user_input=filter_prompt)
            filters = result.filters
    except Exception as e:
        logging.warning(f"Failed to call LM for filters: {e}")
        return None

    if not isinstance(filters, list):
        logging.warning(f"Generated filters is not a list: {filters}")
        return None

    for f in filters:
        if isinstance(f, dict):
            f["dataset_id"] = search_task.dataset_id
    if not filters:
        logging.warning(f"Failed to generate filters: empty result")
    return filters
