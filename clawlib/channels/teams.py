"""Microsoft Teams channel using Bot Framework REST API.

Receives activities via gateway webhook, sends replies via Bot Framework Connector.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from clawlib.bus import MessageBus, OutboundMessage
from clawlib.channels.base import BaseChannel
from clawlib.config.schema import TeamsConfig

TOKEN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"


class TeamsChannel(BaseChannel):
    """
    Microsoft Teams channel (Bot Framework).

    Receives messages via gateway webhook (pushed to agent over control plane).
    Sends replies via Bot Framework Connector REST API.
    """

    name = "teams"

    def __init__(
        self,
        config: TeamsConfig,
        bus: MessageBus,
        workspace: Path | None = None,
    ):
        super().__init__(config, bus, workspace)
        self.config: TeamsConfig = config
        self._http: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._context: dict[str, dict[str, Any]] = {}  # conversation_id -> {service_url, ...}

    def store_context(self, conversation_id: str, context: dict[str, Any]) -> None:
        """Store conversation context for sending replies. Called when receiving a Teams message."""
        self._context[conversation_id] = context

    async def _ensure_token(self) -> str | None:
        """Get or refresh Bot Framework OAuth token."""
        if not self.config.app_id or not self.config.app_password:
            return None
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        try:
            resp = await self._http.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.config.app_id,
                    "client_secret": self.config.app_password,
                    "scope": "https://api.botframework.com/.default",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("access_token")
            return self._token
        except Exception as e:
            logger.error("Teams token fetch failed: {}", e)
            return None

    async def start(self) -> None:
        """Teams channel does not run a loop — it receives via webhook push."""
        self._running = True
        self._http = httpx.AsyncClient(timeout=30.0)
        logger.info("Teams channel ready (webhook-based)")

    async def stop(self) -> None:
        """Stop the Teams channel."""
        self._running = False
        if self._http:
            await self._http.aclose()
            self._http = None

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message via Bot Framework Connector API."""
        if not self._http:
            return

        ctx = self._context.get(msg.chat_id)
        if not ctx:
            logger.warning("Teams: no context for conversation {}, cannot send", msg.chat_id)
            return

        service_url = ctx.get("service_url", "").rstrip("/")
        conversation_id = ctx.get("conversation_id", msg.chat_id)
        if not service_url:
            logger.warning("Teams: missing service_url in context")
            return

        token = await self._ensure_token()
        if not token:
            return

        url = f"{service_url}v3/conversations/{conversation_id}/activities"
        payload = {
            "type": "message",
            "text": msg.content,
        }

        try:
            resp = await self._http.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
        except Exception as e:
            logger.error("Teams send failed: {}", e)
