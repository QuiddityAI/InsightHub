Note that model class names like Mistral_Mistral_Small are persisted in the database (in CollectionColumn.parameters and CollectionItem.column_data), so we need an alias strategy.

Plan: Replace LLMonkey with litellm via litellmonkey adapter
TL;DR: Create a new litellmonkey Python module that reimplements the BaseLLMModel interface on top of litellm. Model definitions move from ~90 Python classes to a single YAML config file where each entry is litellm_kwargs + metadata (price, capabilities, location, etc.). The backend's ~16 files need only import-path changes. A backward-compat alias map handles old class-name IDs persisted in the DB.

Steps

1. Create YAML config file
Create backend/config/llm_models.yaml with entries like:


# Each key is the litellm model string (new canonical ID)mistral/mistral-small-latest:  verbose_name: "Mistral Small"  description: "Fast, cost-effective model"  max_input_tokens: 32000  euro_per_1M_input_tokens: 0.2  euro_per_1M_output_tokens: 0.6  capabilities: [chat]  location: EU  litellm_kwargs:    # Any extra kwargs passed to litellm.completion/embedding    # api_key and api_base are auto-resolved by litellm from env vars    # but can be overridden here if needed  aliases:    - Mistral_Mistral_Small  # old LLMonkey class name
Migrate all ~90 model definitions from llms into this file. Each provider's models are just entries differing in their litellm model prefix (mistral/, openai/, vertex_ai/, groq/, deepinfra/, etc.).

2. Create litellmonkey Python module
Create backend/litellmonkey/ with these files:

__init__.py — exports LiteLLModel, ModelConfig, response types
models.py — Pydantic data models, reusing the same shapes as LLMonkey's ModelConfig, ChatResponse, PromptMessage, TokenUsage, EmbeddingResponse, RerankResponse, RerankItem, ModelCapabilities, ModelLocation. These can start as direct copies from models.py and be simplified over time.
config.py — Loads llm_models.yaml, builds a registry dict, handles alias resolution. Exposes get_model_config(model_id) -> ModelConfig and get_all_model_configs() -> dict.
llm.py — The LiteLLModel class (replaces BaseLLMModel). Single class, no subclasses. Instantiated with a model ID string.
3. Implement LiteLLModel class — the core replacement
LiteLLModel reimplements the BaseLLMModel interface:

Method	Implementation
__init__(model_id)	Resolves aliases (old class names → litellm IDs), loads config from YAML registry
load(model_id)	Class method, same as __init__ — return LiteLLModel(model_id)
available_models()	Returns {model_id: LiteLLModel} for all YAML entries
available_model_configs()	Returns serialized config dicts from YAML (same shape as current)
generate_prompt_response(user_prompt, system_prompt, image, temperature, max_tokens, api_key)	Builds messages list → litellm.completion(**self.litellm_kwargs, messages=..., temperature=..., max_tokens=...) → wraps response in ChatResponse
generate_chat_response(conversation, temperature, max_tokens, api_key)	Same, but takes List[PromptMessage] directly
generate_structured_response(data_model, user_prompt, ...)	Uses litellm.completion() with response_format={"type": "json_object"} or litellm.completion() + JSON parsing with json_repair + Pydantic validation (matching current retry logic)
generate_structured_array_response(data_model, user_prompt, ..., as_dicts)	Same pattern for arrays
generate_short_text(user_prompt, ...)	Port from ConvenienceLLMMixin — wraps generate_prompt_response with retries + output stripping
generate_embeddings(text)	litellm.embedding(model=..., input=[text]) → EmbeddingResponse
rerank(query, documents, top_n, ...)	litellm.rerank(model=..., query=..., documents=...) → RerankResponse (litellm supports Cohere rerank; for others, may need custom handling)
to_litellm()	Returns {"model": self.model_id, **self.litellm_kwargs} — trivial now since model IDs already are litellm strings
config	Property returning the ModelConfig loaded from YAML
Key implementation detail: litellm.completion() already handles the provider dispatch, API key resolution (from env vars like MISTRAL_API_KEY, OPENAI_API_KEY, GOOGLE_APPLICATION_CREDENTIALS), retries, and rate limiting. This eliminates the entire providers layer.

4. Handle backward-compatible alias resolution
In litellmonkey/config.py:

Build a reverse map from YAML aliases → canonical litellm model ID
LiteLLModel.load("Mistral_Mistral_Small") → resolves to "mistral/mistral-small-latest" → works
This means no DB migration is required for existing CollectionColumn.parameters or CollectionItem.column_data — old IDs still resolve
5. Update backend imports (~16 files)
Replace all imports from llmonkey with litellmonkey:

Current import	New import
from llmonkey.llms.base_llm import BaseLLMModel	from litellmonkey import LiteLLModel as BaseLLMModel
from llmonkey.llms.google import Google_Gemini_Flash_1_5_v1	Remove; use LiteLLModel("vertex_ai/gemini-1.5-flash") instead
from llmonkey.models import ChatResponse, PromptMessage	from litellmonkey.models import ChatResponse, PromptMessage
Specific files to update:

utils.py — Change BaseLLMModel import
llm.py — Update default model name strings to litellm IDs (e.g., "Mistral_Ministral8b" → "mistral/ministral-8b-latest")
views.py — Update import + available_llm_models endpoint
llm_column.py — Update import; BaseLLMModel.load(model_name) still works via aliases
extract_filters.py — Replace Google_Gemini_Flash_1_5_v1() with LiteLLModel("vertex_ai/gemini-1.5-flash-001")
approve_items_and_exit_search.py — Indirect via get_default_dspy_llm, just import change
execute_search.py — Same
writing_task.py — Update import
logic.py — Indirect, import change
create_columns.py — Indirect, import change
exhaustive_search.py — Indirect
exhaustive_search_with_answer.py — Indirect
agent_api.py — Uses __class__.__name__ for config; needs update
research_agent.py — Same
office_documents.py — Indirect
tenders.py — Indirect
embeddings.py — Update LLMONKEY_DEEPINFRA_API_KEY env var reference
6. Update frontend hardcoded model defaults
In AddColumnDialog.vue (lines 54-57), update the hardcoded default_models array from class names to litellm IDs.

7. Update environment variables
Rename in .env, required_environment_variables.txt, docker-compose.override.pdferret.yaml, and any deployment configs:

Old	New (litellm standard)
LLMONKEY_OPENAI_API_KEY	OPENAI_API_KEY
LLMONKEY_MISTRAL_API_KEY	MISTRAL_API_KEY
LLMONKEY_GROQ_API_KEY	GROQ_API_KEY
LLMONKEY_DEEPINFRA_API_KEY	DEEPINFRA_API_KEY
LLMONKEY_NEBIUS_API_KEY	NEBIUS_API_KEY
LLMONKEY_AZURE_API_KEY	AZURE_API_KEY
LLMONKEY_AZURE_OPENAI_URL	AZURE_API_BASE
LLMONKEY_GOOGLE_PROJECT_ID	VERTEXAI_PROJECT
LLMONKEY_GOOGLE_LOCATION	VERTEXAI_LOCATION
8. Update pyproject.toml dependency
In pyproject.toml: remove llmonkey @ InsightHub. dependency, add litellm, pyyaml, json-repair. Keep pydantic (already required).

9. Remove LLMonkey submodule/dependency
The LLMonkey directory can be kept temporarily for reference and removed once migration is validated.

Verification

Unit tests: Create backend/litellmonkey/tests/ with tests for:
Config loading + alias resolution (old class names → litellm IDs)
to_litellm() returns correct dict
generate_prompt_response calls litellm.completion with correct args (mock litellm)
generate_structured_response JSON parsing + retry logic
available_model_configs() returns expected shape for frontend
Integration test: Verify the /api/v1/columns/available_llm_models endpoint still returns valid configs
Manual test: Create an LLM column, select a model, process a cell — verify output and cost tracking
Backward compat test: Create a column with an old-style model ID string, verify it resolves correctly
DSPy test: Verify dspy.LM(**model.to_litellm()) still works for a few representative tasks (e.g., search query generation)
Decisions

Litellm model strings as canonical IDs (user chose this) — cleaner long term, alias map handles old DB records
No DB migration needed — alias resolution in config makes old persisted class names still work
YAML config — human-readable, supports comments for documenting models
Standard litellm env vars — simplifies setup, litellm auto-resolves them
Full scope — embeddings and reranking included in replacement
Single class, no subclasses — the 90 model classes collapse into YAML entries + one LiteLLModel class
Provider layer eliminated — litellm handles all provider dispatch internally