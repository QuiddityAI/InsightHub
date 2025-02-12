import logging
import re

from llmonkey.llms import Google_Gemini_Flash_1_5_v1

from data_map_backend.models import DataCollection, Dataset
from search.schemas import Filter, SearchTaskSettings

# TODO: migrate to DSPy + optimize prompts + re-enable feature


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


def extract_filters(search_task: SearchTaskSettings, filter_prompt: str):
    filters, response = Google_Gemini_Flash_1_5_v1().generate_structured_array_response(
        Filter, filter_prompt, as_dicts=True
    )
    for filter in filters:
        assert isinstance(filter, dict)
        filter["dataset_id"] = search_task.dataset_id
    if filters is None:
        logging.warning(f"Failed to generate filters: {response}")
    return filters
