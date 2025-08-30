import os
import box

from llmonkey.llms.base_llm import BaseLLMModel
from llmonkey.models import ModelConfig, ModelCapabilities, ModelLocation
from llmonkey.providers import ModelProvider


class Deepinfra_GPTOSS120b_Low(BaseLLMModel):
    provider = ModelProvider.deepinfra  # type: ignore
    config = ModelConfig(  # type: ignore
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

    extra_kwargs = {"reasoning_effort": "low"}

    def to_litellm(self) -> dict:
        kwargs = super().to_litellm()
        kwargs.update(
            {
                "reasoning_effort": "low",
                "allowed_openai_params": ["reasoning_effort"],
                "temperature": 0.1,
            }
        )
        kwargs.update(self.extra_kwargs)
        return kwargs


class Deepinfra_GPTOSS120b_Medium(Deepinfra_GPTOSS120b_Low):
    extra_kwargs = {"reasoning_effort": "medium"}


class Deepinfra_GPTOSS120b_High(Deepinfra_GPTOSS120b_Low):
    extra_kwargs = {"reasoning_effort": "high"}


class Deepinfra_Deepseek_V31(BaseLLMModel):
    provider = ModelProvider.deepinfra  # type: ignore
    config = ModelConfig(  # type: ignore
        identifier="deepseek-ai/DeepSeek-V3.1",
        verbose_name="Deepinfra Deepseek v3.1",
        description="DeepSeek-V3.1 is a hybrid model that supports both thinking mode and non-thinking mode",
        max_input_tokens=131072,
        euro_per_1M_input_tokens=0.3,
        euro_per_1M_output_tokens=1.0,
        capabilities=[ModelCapabilities.chat],
        location=ModelLocation.US,
        parameters="671B",
    )

    extra_kwargs = {"reasoning_effort": "low"}

    def to_litellm(self) -> dict:
        kwargs = super().to_litellm()
        kwargs.update(
            {
                "reasoning_effort": "low",
                "allowed_openai_params": ["reasoning_effort"],
                "temperature": 0.1,
            }
        )
        kwargs.update(self.extra_kwargs)
        return kwargs



default_models = box.Box(
    {
        "small": "Deepinfra_GPTOSS120b_Low",
        "medium": "Deepinfra_GPTOSS120b_Medium",
        "large": "Deepinfra_GPTOSS120b_High",
    }
)

# supports direct kwargs for litellm or llmonkey model name
default_dspy_models = box.Box(
    {
        "column_title": "Deepinfra_GPTOSS120b_Low",
        "column_language": "Deepinfra_GPTOSS120b_Low",
        "query_language": "Deepinfra_GPTOSS120b_Low",
        "doc_comparison": "Deepinfra_GPTOSS120b_High",
        "search_query": "Deepinfra_GPTOSS120b_Medium",
        "tender_summary": "Deepinfra_GPTOSS120b_Low",
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
            "allowed_openai_params": ["reasoning_effort"],
        },
    }
)
