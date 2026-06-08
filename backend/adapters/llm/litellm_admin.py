"""LiteLLM Admin API wrapper.

Provides async helpers for the LiteLLM proxy management endpoints
(team management, key generation, spend tracking).  All calls are
authenticated with the proxy master key.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LiteLLMAdmin:
    """Async wrapper around the LiteLLM proxy management API.

    Parameters
    ----------
    base_url : str
        Root URL of the LiteLLM proxy (e.g. ``http://localhost:4000``).
    master_key : str
        The ``master_key`` configured in ``general_settings``.
    """

    def __init__(self, base_url: str, master_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.master_key = master_key

    # ── internal helpers ───────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        """Return common auth headers for every request."""
        return {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        """Build the full URL for a given API path."""
        return f"{self.base_url}{path}"

    # ── health check ──────────────────────────────────────────────────────

    async def check_health(self) -> dict[str, Any]:
        """Ping the LiteLLM proxy ``/health`` endpoint.

        Returns
        -------
        dict
            JSON response from the proxy (typically contains model
            health statuses) or a dict with ``status: "unavailable"``
            if the proxy cannot be reached.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._url("/health"),
                    headers=self._headers(),
                    timeout=5.0,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "LiteLLM health check failed: %s — %s",
                exc.response.status_code,
                exc.response.text,
            )
            return {"status": "unhealthy", "error": str(exc)}
        except httpx.RequestError as exc:
            logger.warning("LiteLLM proxy unreachable: %s", exc)
            return {"status": "unavailable", "error": str(exc)}

    # ── team management ────────────────────────────────────────────────────

    async def create_team(
        self,
        team_alias: str,
        models: list[str],
        max_budget: float | None = None,
        budget_duration: str | None = None,
    ) -> dict[str, Any]:
        """Create a new team with access to *models*.

        Parameters
        ----------
        team_alias : str
            Human-readable name for the team.
        models : list[str]
            Model names (from ``model_list``) the team may access.
        max_budget : float | None
            Optional maximum budget in USD.
        budget_duration : str | None
            Optional budget duration (e.g. '30d').

        Returns
        -------
        dict
            JSON response from the proxy containing ``team_id`` etc.
        """
        payload: dict[str, Any] = {
            "team_alias": team_alias,
            "models": models,
        }
        if max_budget is not None:
            payload["max_budget"] = max_budget
        if budget_duration is not None:
            payload["budget_duration"] = budget_duration

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._url("/team/new"),
                    headers=self._headers(),
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                logger.info("Created team '%s' → %s", team_alias, data.get("team_id"))
                return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to create team '%s': %s — %s",
                team_alias,
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("Network error creating team '%s': %s", team_alias, exc)
            raise

    async def list_teams(self) -> list[dict[str, Any]]:
        """List all teams registered on the proxy.

        Returns
        -------
        list[dict]
            Each dict contains ``team_id``, ``team_alias``, ``models``, etc.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._url("/team/list"),
                    headers=self._headers(),
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                # The proxy may return the list directly or nested under a key.
                if isinstance(data, list):
                    return data
                return data.get("teams", data.get("data", []))
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to list teams: %s — %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("Network error listing teams: %s", exc)
            raise

    async def delete_team(self, team_id: str) -> dict[str, Any]:
        """Delete a team by its ID.

        Parameters
        ----------
        team_id : str
            The ``team_id`` returned when the team was created.

        Returns
        -------
        dict
            JSON response confirming deletion.
        """
        payload: dict[str, Any] = {"team_ids": [team_id]}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._url("/team/delete"),
                    headers=self._headers(),
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                logger.info("Deleted team %s", team_id)
                return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to delete team '%s': %s — %s",
                team_id,
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("Network error deleting team '%s': %s", team_id, exc)
            raise

    # ── key management ─────────────────────────────────────────────────────

    async def generate_key(
        self,
        user_id: str,
        team_id: str,
        models: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a new API key scoped to a user and team.

        Parameters
        ----------
        user_id : str
            Unique identifier for the end-user.
        team_id : str
            Team the key should be associated with.
        models : list[str] | None
            Optional model allow-list.  Inherits team models when *None*.

        Returns
        -------
        dict
            JSON response containing ``key``, ``token``, etc.
        """
        payload: dict[str, Any] = {
            "user_id": user_id,
            "team_id": team_id,
        }
        if models is not None:
            payload["models"] = models

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._url("/key/generate"),
                    headers=self._headers(),
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                logger.info(
                    "Generated key for user '%s' in team '%s'", user_id, team_id
                )
                return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to generate key for user '%s': %s — %s",
                user_id,
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error(
                "Network error generating key for user '%s': %s", user_id, exc
            )
            raise

    # ── spend tracking ─────────────────────────────────────────────────────

    async def get_spend_logs(
        self,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve spend/usage logs, optionally filtered.

        Parameters
        ----------
        user_id : str | None
            Filter logs to a specific user.
        team_id : str | None
            Filter logs to a specific team.

        Returns
        -------
        list[dict]
            A list of spend log entries.
        """
        params: dict[str, str] = {}
        if user_id is not None:
            params["user_id"] = user_id
        if team_id is not None:
            params["team_id"] = team_id

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._url("/spend/logs"),
                    headers=self._headers(),
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list):
                    return data
                return data.get("logs", data.get("data", []))
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to fetch spend logs: %s — %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("Network error fetching spend logs: %s", exc)
            raise
