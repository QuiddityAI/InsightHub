import os
import box

from llmonkey.llms.base_llm import BaseLLMModel
from llmonkey.models import ModelConfig, ModelCapabilities, ModelLocation
from llmonkey.providers import ModelProvider


class Deepinfra_GPTOSS120b(BaseLLMModel):
    @property
    def provider(self):
        return ModelProvider.deepinfra

    @property
    def config(self) -> ModelConfig:
        return ModelConfig(
            identifier="openai/gpt-oss-120b",
            verbose_name="Deepinfra OpenAI GPT-OSS-120b",
            description="gpt-oss-120b is an open-weight, 117B-parameter Mixture-of-Experts (MoE) language model from OpenAI designed for high-reasoning, agentic, and general-purpose production use cases. The model supports configurable reasoning depth, full chain-of-thought access, and native tool use, including function calling, browsing, and structured output generation.",
            max_input_tokens=131072,
            euro_per_1M_input_tokens=0.09,
            euro_per_1M_output_tokens=0.45,
            capabilities=[ModelCapabilities.chat],
            location=ModelLocation.US,
            parameters="120B",
        )

    def to_litellm(self) -> dict:
        kwargs = super().to_litellm()
        kwargs.update(
            {
                "reasoning_effort": "low",
                "allowed_openai_params": ['reasoning_effort'],
                "temperature": 0.1,
            }
        )
        return kwargs


default_models = box.Box(
    {
        "small": "Deepinfra_GPTOSS120b",
        "medium": "Deepinfra_GPTOSS120b",
        "large": "Deepinfra_GPTOSS120b",
    }
)

# supports direct kwargs for litellm or llmonkey model name
default_dspy_models = box.Box(
    {
        "column_title": "Deepinfra_GPTOSS120b",
        "column_language": "Deepinfra_GPTOSS120b",
        "query_language": "Deepinfra_GPTOSS120b",
        "doc_comparison": "Deepinfra_GPTOSS120b",
        "search_query": "Deepinfra_GPTOSS120b",
        "tender_summary": "Deepinfra_GPTOSS120b",
    }
)

default_pdferret_models = box.Box(
    {
        "vision": "Mistral_Mistral_Small",
        "text": "Mistral_Pixtral",
    }
)

# for deepinfra
# 'model': 'openai/openai/gpt-oss-120b',
# 'api_key': os.environ.get("LLMONKEY_DEEPINFRA_API_KEY", ""),
# 'api_base': 'https://api.deepinfra.com/v1/openai',

# {'model': 'openai/mistral-large-latest',
# 'api_key': os.environ.get("LLMONKEY_MISTRAL_API_KEY", ""),
# 'api_base': 'https://api.mistral.ai/v1'}

default_mistral_ocr_models = box.Box(
    {
        "ocr": "mistral-ocr-latest",
        "api_key": os.environ.get("LLMONKEY_MISTRAL_API_KEY", ""),
        "metadata_llm_kwargs": {
            "model": "openai/openai/gpt-oss-120b",
            "temperature": 0.1,
            "max_tokens": 4096,
            "api_key": os.environ.get("LLMONKEY_DEEPINFRA_API_KEY", ""),
            "api_base": "https://api.deepinfra.com/v1/openai",
            "reasoning_effort": "low",
            "allowed_openai_params": ['reasoning_effort']
        },
    }
)
