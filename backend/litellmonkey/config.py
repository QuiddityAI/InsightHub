import logging
import os
from pathlib import Path

import yaml

from litellmonkey.models import ModelCapabilities, ModelConfig, ModelLocation

logger = logging.getLogger(__name__)

# Defaults to the sibling config/ dir; LLM_MODELS_CONFIG_PATH lets a host app
# (e.g. pdferret, which vendors this package) point at its own registry.
_CONFIG_PATH = Path(
    os.environ.get("LLM_MODELS_CONFIG_PATH")
    or Path(__file__).resolve().parent.parent / "config" / "llm_models.yaml"
)

_registry: dict[str, dict] = {}  # canonical_id -> raw YAML dict
_alias_map: dict[str, str] = {}  # alias -> canonical_id
_model_configs: dict[str, ModelConfig] = {}  # canonical_id -> ModelConfig
_defaults: dict[str, dict[str, str]] = {}  # section -> {key -> model_id}
_loaded = False


def _resolve_env_vars(value):
    """Resolve ${ENV_VAR} / ${ENV_VAR:-default} references in a string."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        expr = value[2:-1]
        env_var, sep, default = expr.partition(":-")
        resolved = os.environ.get(env_var, "")
        if not resolved and sep:
            return default
        return resolved
    return value


def _load():
    global _registry, _alias_map, _model_configs, _defaults, _loaded
    if _loaded:
        return

    raw = yaml.safe_load(_CONFIG_PATH.read_text())

    # Extract defaults section (not a model entry)
    _defaults = raw.pop("defaults", {})

    for canonical_id, entry in raw.items():
        _registry[canonical_id] = entry

        # Build alias map
        for alias in entry.get("aliases", []):
            _alias_map[alias] = canonical_id
        _alias_map[canonical_id] = canonical_id

        # Resolve env var references in litellm_kwargs
        litellm_kwargs = dict(entry.get("litellm_kwargs", {}) or {})
        for k, v in litellm_kwargs.items():
            litellm_kwargs[k] = _resolve_env_vars(v)
        entry["_resolved_litellm_kwargs"] = litellm_kwargs

        # Get pricing and context window from litellm if not overridden in YAML
        max_input_tokens = entry.get("max_input_tokens")
        usd_input = entry.get("usd_per_1M_input_tokens")
        usd_output = entry.get("usd_per_1M_output_tokens")

        if max_input_tokens is None or usd_input is None or usd_output is None:
            try:
                import litellm

                # Use the actual litellm model string for lookup
                lookup_model = entry.get("litellm_model", canonical_id)
                info = litellm.get_model_info(lookup_model)
                if max_input_tokens is None:
                    max_input_tokens = info.get("max_input_tokens") or info.get("max_tokens", 4096)
                if usd_input is None:
                    usd_input = (info.get("input_cost_per_token") or 0) * 1_000_000
                if usd_output is None:
                    usd_output = (info.get("output_cost_per_token") or 0) * 1_000_000
            except Exception:
                logger.warning(f"litellm.get_model_info() failed for {canonical_id}, using defaults")
                max_input_tokens = max_input_tokens or 4096
                usd_input = usd_input or 0.0
                usd_output = usd_output or 0.0

        # Parse capabilities
        capabilities = []
        for c in entry.get("capabilities", ["chat"]):
            try:
                capabilities.append(ModelCapabilities(c))
            except ValueError:
                logger.warning(f"Unknown capability '{c}' for model {canonical_id}")

        # Parse location
        location = None
        if entry.get("location"):
            try:
                location = ModelLocation(entry["location"])
            except ValueError:
                logger.warning(f"Unknown location '{entry['location']}' for model {canonical_id}")

        _model_configs[canonical_id] = ModelConfig(
            identifier=canonical_id,
            verbose_name=entry.get("verbose_name", canonical_id),
            description=entry.get("description", ""),
            max_input_tokens=max_input_tokens,
            usd_per_1M_input_tokens=usd_input,
            usd_per_1M_output_tokens=usd_output,
            capabilities=capabilities,
            location=location,
            parameters=entry.get("parameters"),
        )

    _loaded = True


def resolve_alias(model_id: str) -> str:
    """Resolve an alias (old class name or canonical ID) to the canonical litellm ID."""
    _load()
    if model_id in _alias_map:
        return _alias_map[model_id]
    raise ValueError(f"Model '{model_id}' not found in registry or aliases.")


def get_model_config(model_id: str) -> ModelConfig:
    """Get ModelConfig for a model ID (canonical or alias)."""
    _load()
    canonical = resolve_alias(model_id)
    return _model_configs[canonical]


def get_all_model_configs() -> dict[str, ModelConfig]:
    """Get all model configs, keyed by canonical ID."""
    _load()
    return dict(_model_configs)


def get_litellm_kwargs(model_id: str) -> dict:
    """Get extra litellm kwargs for a model (api_base, api_key, etc.)."""
    _load()
    canonical = resolve_alias(model_id)
    return dict(_registry[canonical].get("_resolved_litellm_kwargs", {}))


def get_litellm_model(model_id: str) -> str:
    """Get the actual litellm model string (may differ from canonical_id for custom providers)."""
    _load()
    canonical = resolve_alias(model_id)
    return _registry[canonical].get("litellm_model", canonical)


def get_defaults(section: str) -> dict[str, str]:
    """Get default model assignments for a section (models, dspy, pdferret)."""
    _load()
    return dict(_defaults.get(section, {}))


def get_defaults_list(section: str) -> list[str]:
    """Get a list-valued default section (e.g. fallback_chain)."""
    _load()
    value = _defaults.get(section, [])
    return list(value) if value else []
