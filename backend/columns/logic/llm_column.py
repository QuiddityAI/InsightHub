import json
import logging

import json5
from django.utils import timezone
from llmonkey.llms import BaseLLMModel, Mistral_Mistral_Small

from data_map_backend.models import CollectionColumn, ServiceUsage
from data_map_backend.prompts import table_cell_prompt, table_cell_prompt_de
from columns.prompts import item_relevancy_prompt, item_relevancy_prompt_de
from columns.schemas import CellData, Criterion


def generate_llm_cell_data(input_data: str, column: CollectionColumn, user_id: int, is_relevance_column: bool = False) -> CellData:
    cell_data = CellData(
        changed_at=timezone.now().isoformat(),
        is_ai_generated=True,
        is_computed=True,
        is_manually_edited=False,
    )
    # if not column.parameters.get("model"):
    #     logging.error("No model specified for LLM column.")
    #     cell_data["value"] = "No model specified"
    #     return cell_data
    default_model = Mistral_Mistral_Small.__name__
    model = BaseLLMModel.load(column.parameters.get("model") or default_model)

    # necessary 'AI credits' is defined by us as the cost per 1M tokens / factor:
    ai_credits = model.config.euro_per_1M_output_tokens / 5.0
    usage_tracker = ServiceUsage.get_usage_tracker(user_id, "External AI")
    result = usage_tracker.track_usage(ai_credits, f"extract information using {model.__class__.__name__}")
    if result['approved'] != True:
        cell_data.value = "AI usage limit exceeded"
        return cell_data

    system_prompt = None
    user_prompt = None
    if column.prompt_template:
        system_prompt = column.prompt_template
    elif is_relevance_column:
        translated_prompts = {
            'en': item_relevancy_prompt,
            'de': item_relevancy_prompt_de,
        }
        language = column.parameters.get("language") or "en"
        system_prompt = translated_prompts.get(language, item_relevancy_prompt)
    else:
        translated_prompts = {
            'en': table_cell_prompt,
            'de': table_cell_prompt_de,
        }
        language = column.parameters.get("language") or "en"
        system_prompt = translated_prompts.get(language, table_cell_prompt)

    replacements = [
        ("title", column.name),
        ("expression", column.expression or ""),
        ("document", input_data.strip()),
    ]
    for key, value in replacements:
        system_prompt = system_prompt.replace("{{ " + key + " }}", value)

    if is_relevance_column:
        criteria_review, response = model.generate_structured_array_response(
            Criterion,
            system_prompt=system_prompt,
            user_prompt=user_prompt or "",
            max_tokens=2000,
        )
        relevance_score = len([c.fulfilled for c in criteria_review if c.fulfilled]) / max(len(criteria_review), 1)  # type: ignore
        value = {
            "criteria_review": [c.model_dump() for c in criteria_review],  # type: ignore
            "is_relevant": relevance_score > 0.6,
            "relevance_score": relevance_score,
        }
    else:
        response = model.generate_prompt_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt or "",
            max_tokens=2000,
        )
        response_text = response.conversation[-1].content
        value = response_text

    cell_data.value = value
    cell_data.used_prompt = f"system_prompt:\n{system_prompt}\n---\n\nuser_prompt:\n{user_prompt}"
    return cell_data
