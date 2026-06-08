"""Model registry — central catalog of available LLM models.

For Level 3+ (LiteLLM mode), model IDs are the friendly aliases from
litellm_config.yaml (e.g. 'nova-lite', 'gemini-flash', 'groq-llama').
For Level 2 (direct Bedrock), model IDs are the Bedrock model identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import settings


@dataclass(frozen=True)
class ModelInfo:
    """Immutable descriptor for a supported model."""

    id: str                 # Model ID used in API calls
    display_name: str       # Short human-readable name for the UI
    provider: str           # Cloud provider / vendor
    description: str        # One-liner shown in the model picker
    context_window: int     # Max tokens (for informational display)


# ── Registered models ──────────────────────────────────────────────────────
_BEDROCK_MODELS: dict[str, ModelInfo] = {}
_LITELLM_MODELS: dict[str, ModelInfo] = {}


def _register_bedrock(model: ModelInfo) -> None:
    _BEDROCK_MODELS[model.id] = model


def _register_litellm(model: ModelInfo) -> None:
    _LITELLM_MODELS[model.id] = model


# Bedrock models (Level 2)
_register_bedrock(ModelInfo(
    id="us.amazon.nova-lite-v1:0",
    display_name="Nova Lite",
    provider="Amazon",
    description="Fast, cost-effective model for everyday research tasks",
    context_window=300_000,
))

_register_bedrock(ModelInfo(
    id="minimax.minimax-m2.5",
    display_name="MiniMax M2.5",
    provider="MiniMax",
    description="Advanced reasoning model with 196K context window",
    context_window=196_608,
))

# LiteLLM models (Level 3+) — match names in litellm_config.yaml
_register_litellm(ModelInfo(
    id="nova-lite",
    display_name="Nova Lite",
    provider="Amazon (via LiteLLM)",
    description="Fast, cost-effective model via AWS Bedrock",
    context_window=300_000,
))

_register_litellm(ModelInfo(
    id="gemini-flash",
    display_name="Gemini 2.0 Flash",
    provider="Google (via LiteLLM)",
    description="Google's fast multimodal model with 1M context",
    context_window=1_000_000,
))

_register_litellm(ModelInfo(
    id="groq-llama",
    display_name="Llama 3.3 70B",
    provider="Groq (via LiteLLM)",
    description="Meta's Llama 3.3 70B on Groq's ultra-fast inference",
    context_window=128_000,
))


# ── Public API ─────────────────────────────────────────────────────────────

def _active_registry() -> dict[str, ModelInfo]:
    """Return the model registry matching the current LLM_PROVIDER config."""
    if settings.LLM_PROVIDER.lower() == "litellm":
        return _LITELLM_MODELS
    return _BEDROCK_MODELS


def list_models() -> list[ModelInfo]:
    """Return all registered models as an ordered list."""
    return list(_active_registry().values())


def get_model(model_id: str) -> ModelInfo:
    """Look up a model by its ID.

    Raises:
        ValueError: If the model_id is not in the registry.
    """
    registry = _active_registry()
    if model_id not in registry:
        valid = ", ".join(registry.keys())
        raise ValueError(
            f"Unknown model '{model_id}'. Available models: {valid}"
        )
    return registry[model_id]


def _default_model_id() -> str:
    """Return the default model ID for the active provider."""
    if settings.LLM_PROVIDER.lower() == "litellm":
        return "gemini-flash"
    return "us.amazon.nova-lite-v1:0"


DEFAULT_MODEL_ID: str = _default_model_id()
