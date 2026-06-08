"""Health check route."""

from fastapi import APIRouter

from adapters.llm.litellm_admin import LiteLLMAdmin
from config import settings

router = APIRouter(tags=["health"])

_admin = LiteLLMAdmin(
    base_url=settings.LITELLM_BASE_URL,
    master_key=settings.LITELLM_MASTER_KEY,
)


@router.get("/health")
async def health_check() -> dict:
    """Return service health status including LiteLLM proxy status."""
    litellm_health = await _admin.check_health()
    litellm_status = litellm_health.get("status", "unknown")
    # Normalize: LiteLLM returns various shapes — if we got a valid
    # response without an error key, it's healthy.
    if "error" not in litellm_health and litellm_status not in ("unhealthy", "unavailable"):
        litellm_status = "ok"

    return {
        "status": "ok",
        "litellm_status": litellm_status,
    }
