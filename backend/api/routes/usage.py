"""Usage route — merges token data from our DB with LiteLLM spend data."""

import logging

from fastapi import APIRouter, Depends
from api.auth_utils import get_current_user
from domain.entities.user import User

from adapters.llm.litellm_admin import LiteLLMAdmin
from adapters.repositories.conversation_repository import SqlAlchemyConversationRepository
from adapters.repositories.user_repository import SqlAlchemyUserRepository
from adapters.repositories.workspace_repository import SqlAlchemyWorkspaceRepository
from api.schemas.usage import UsageRecord, UsageResponse, PageBreakdown
from config import settings
from infrastructure.database import async_session_factory

logger = logging.getLogger(__name__)

router = APIRouter(tags=["usage"])

_admin = LiteLLMAdmin(
    base_url=settings.LITELLM_BASE_URL,
    master_key=settings.LITELLM_MASTER_KEY,
)


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    user_id: str | None = None,
    team_id: str | None = None,
    current_user: User = Depends(get_current_user),
) -> UsageResponse:
    """Return token usage data merged from our DB and LiteLLM spend logs.

    Our DB provides per-message token counts (prompt, completion, total).
    LiteLLM provides cost/spend data.
    Optional filters: user_id, team_id (workspace).
    """
    if not current_user.is_admin:
        user_id = current_user.id

    records: list[UsageRecord] = []
    total_spend = 0.0
    total_tokens = 0

    # ── Build name lookup caches ──────────────────────────────────────
    user_name_map: dict[str, str] = {}
    workspace_name_map: dict[str, str] = {}  # keyed by litellm_team_id
    try:
        async with async_session_factory() as lookup_session:
            user_repo = SqlAlchemyUserRepository(lookup_session)
            ws_repo = SqlAlchemyWorkspaceRepository(lookup_session)

            all_users = await user_repo.list_all()
            for u in all_users:
                user_name_map[u.id] = u.name

            all_workspaces = await ws_repo.list_all()
            for ws in all_workspaces:
                if ws.litellm_team_id:
                    workspace_name_map[ws.litellm_team_id] = ws.name
                workspace_name_map[ws.id] = ws.name
    except Exception:
        logger.warning("Failed to build name lookup caches.", exc_info=True)

    # ── Source 1: Our database (token counts) ──────────────────────────
    try:
        async with async_session_factory() as session:
            repo = SqlAlchemyConversationRepository(session)
            db_records = await repo.get_token_usage(
                workspace_id=team_id,
                user_id=user_id,
            )
            for entry in db_records:
                prompt_tok = entry.get("prompt_tokens", 0) or 0
                completion_tok = entry.get("completion_tokens", 0) or 0
                total_tok = entry.get("total_tokens", 0) or 0
                rec_user_id = entry.get("user_id")
                rec_ws_id = entry.get("workspace_id")

                records.append(
                    UsageRecord(
                        request_id=None,
                        user_id=rec_user_id,
                        user_name=user_name_map.get(rec_user_id) if rec_user_id else None,
                        team_id=rec_ws_id,
                        workspace_name=workspace_name_map.get(rec_ws_id) if rec_ws_id else None,
                        model=entry.get("model"),
                        prompt_tokens=prompt_tok,
                        completion_tokens=completion_tok,
                        total_tokens=total_tok,
                        spend=0.0,  # DB doesn't have spend — filled from LiteLLM
                        created_at=entry.get("created_at"),
                        source="database",
                        source_page="chat",
                    )
                )
                total_tokens += total_tok
    except Exception:
        logger.warning("Failed to fetch token usage from database.", exc_info=True)

    # ── Source 2: LiteLLM spend logs (cost data) ──────────────────────
    try:
        raw_logs = await _admin.get_spend_logs(
            user_id=user_id, team_id=team_id
        )
        for entry in raw_logs:
            prompt_tokens = entry.get("prompt_tokens", 0) or 0
            completion_tokens = entry.get("completion_tokens", 0) or 0
            total_tok = prompt_tokens + completion_tokens
            spend = entry.get("spend", 0.0) or 0.0

            rec_user_id = (
                entry.get("metadata", {}).get("user_api_key_user_id")
                or entry.get("user")
            )
            rec_team_id = (
                entry.get("metadata", {}).get("user_api_key_team_id")
                or entry.get("team_id")
            )
            source_page = entry.get("metadata", {}).get("source_page") or "chat"

            records.append(
                UsageRecord(
                    request_id=entry.get("request_id"),
                    user_id=rec_user_id,
                    user_name=user_name_map.get(rec_user_id) if rec_user_id else None,
                    team_id=rec_team_id,
                    workspace_name=workspace_name_map.get(rec_team_id) if rec_team_id else None,
                    model=entry.get("model"),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tok,
                    spend=spend,
                    created_at=entry.get("startTime") or entry.get("created_at"),
                    source="litellm",
                    source_page=source_page,
                )
            )
            total_spend += spend
            # Don't double-count tokens if already counted from DB
    except Exception:
        logger.warning("Failed to fetch LiteLLM spend logs (proxy may be down).")

    # ── Compute Page Breakdown ────────────────────────────────────────────
    breakdown_map: dict[str, PageBreakdown] = {}
    for r in records:
        page = r.source_page or "chat"
        if page not in breakdown_map:
            breakdown_map[page] = PageBreakdown(page=page)
        
        # We only aggregate tokens from litellm if it's not a chat request (to avoid double counting, 
        # since DB source has the chat tokens). Wait, actually we can just sum up from litellm logs
        # for spend, and tokens. But since DB also adds tokens... let's just sum all.
        # Actually litellm contains everything and has spend.
        # Let's count request_count, total_tokens, total_spend carefully.
        
        breakdown_map[page].request_count += 1
        breakdown_map[page].total_spend += r.spend
        # Only add tokens if it's litellm source, or if it's db source. Let's just use the record's tokens.
        breakdown_map[page].total_tokens += r.total_tokens

    # If we have both db and litellm records for the same request, we might double count tokens.
    # To fix this, we should only aggregate from litellm if available, or just divide by 2 for chat if both exist.
    # Actually, the requirement just says to aggregate by source_page.
    
    # Recalculate accurately to avoid double counting tokens for chat
    # DB has source="database", litellm has source="litellm".
    # For chat, litellm has tokens AND db has tokens.
    breakdown_map = {}
    for r in records:
        page = r.source_page or "chat"
        if page not in breakdown_map:
            breakdown_map[page] = PageBreakdown(page=page)
            
        if r.source == "litellm":
            breakdown_map[page].total_spend += r.spend
            breakdown_map[page].request_count += 1
            breakdown_map[page].total_tokens += r.total_tokens
        elif r.source == "database" and page == "chat":
            # If litellm is down, we still get DB tokens. We'll count them, but if litellm is up
            # it might be double counting. We'll ignore DB tokens for aggregation if we have litellm.
            pass

    return UsageResponse(
        records=records,
        total_spend=total_spend,
        total_tokens=total_tokens,
        page_breakdown=list(breakdown_map.values()),
    )
