"""Zalo Official Account (Bot API) channel implementation.

Uses long-polling (getUpdates) to receive messages and sendMessage/sendPhoto to send.
Based on OpenClaw's Zalo integration: https://docs.openclaw.ai/channels/zalo
API docs: https://bot.zapps.me/docs/
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from clawlib.bus import MessageBus, OutboundMessage
from clawlib.channels.base import BaseChannel
from clawlib.config.schema import ZaloConfig

ZALO_API_BASE = "https://bot-api.zaloplatforms.com/bot"
MAX_TEXT_LEN = 2000  # Zalo API limit


def _split_message(content: str, max_len: int = MAX_TEXT_LEN) -> list[str]:
    """Split content into chunks within max_len, preferring line breaks."""
    if not content or len(content) <= max_len:
        return [content] if content else []
    chunks: list[str] = []
    while content:
        if len(content) <= max_len:
            chunks.append(content)
            break
        cut = content[:max_len]
        pos = cut.rfind("\n")
        if pos == -1:
            pos = cut.rfind(" ")
        if pos == -1:
            pos = max_len
        chunks.append(content[:pos])
        content = content[pos:].lstrip()
    return chunks


class ZaloChannel(BaseChannel):
    """
    Zalo Official Account channel using long-polling (getUpdates).

    No public IP or webhook required. Text is chunked to 2000 chars (Zalo limit).
    """

    name = "zalo"

    def __init__(
        self,
        config: ZaloConfig,
        bus: MessageBus,
        workspace: Path | None = None,
    ):
        super().__init__(config, bus, workspace)
        self.config: ZaloConfig = config
        self._http: httpx.AsyncClient | None = None
        self._poll_task: asyncio.Task | None = None

    def _api_url(self, method: str) -> str:
        return f"{ZALO_API_BASE}{self.config.bot_token}/{method}"

    def _is_group_allowed(self, sender_id: str) -> bool:
        """Check if sender is allowed in group chats per group_policy."""
        if self.config.group_policy == "disabled":
            return False
        if self.config.group_policy == "open":
            return True
        # allowlist: use group_allow_from or fall back to allow_from
        allow = self.config.group_allow_from or self.config.allow_from
        if not allow:
            return False
        return str(sender_id) in allow

    def is_allowed(self, sender_id: str) -> bool:
        """Check if a sender is allowed (DM or group)."""
        allow = self.config.allow_from
        if not allow:
            return True
        sender_str = str(sender_id)
        if sender_str in allow:
            return True
        if "|" in sender_str:
            for part in sender_str.split("|"):
                if part and part in allow:
                    return True
        return False

    async def start(self) -> None:
        """Start the Zalo channel with long-polling."""
        if not self.config.bot_token:
            logger.error("Zalo bot_token not configured")
            return

        self._running = True
        self._http = httpx.AsyncClient(timeout=60.0)

        logger.info("Starting Zalo channel (long-polling)...")

        while self._running:
            try:
                resp = await self._http.post(
                    self._api_url("getUpdates"),
                    json={"timeout": "30"},
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok"):
                    logger.warning("Zalo getUpdates returned ok=false: {}", data)
                    await asyncio.sleep(5)
                    continue

                result = data.get("result")
                if not result:
                    continue

                # Result can be single object or array
                events = result if isinstance(result, list) else [result]
                for ev in events:
                    try:
                        await self._handle_update(ev)
                    except Exception as e:
                        logger.error("Error handling Zalo update: {}", e)

            except asyncio.CancelledError:
                break
            except httpx.HTTPStatusError as e:
                logger.warning("Zalo API error: {}", e.response.status_code)
                await asyncio.sleep(5)
            except Exception as e:
                logger.warning("Zalo poll error: {}", e)
                if self._running:
                    await asyncio.sleep(5)

    async def _handle_update(self, ev: dict[str, Any]) -> None:
        """Process one update from getUpdates (same format as webhook)."""
        event_name = ev.get("event_name", "")
        msg = ev.get("message")
        if not msg:
            if event_name == "message.sticker.received":
                logger.debug("Zalo sticker received (not processed)")
            elif event_name == "message.unsupported.received":
                logger.debug("Zalo unsupported message (protected user)")
            return

        from_info = msg.get("from", {})
        chat_info = msg.get("chat", {})
        sender_id = from_info.get("id", "")
        chat_id = chat_info.get("id", sender_id)
        chat_type = chat_info.get("chat_type", "PRIVATE")
        is_group = chat_type == "GROUP"

        if is_group:
            if self.config.group_policy == "disabled":
                return
            if not self._is_group_allowed(sender_id):
                return

        if not is_group and not self.is_allowed(sender_id):
            logger.warning(
                "Zalo access denied for sender {} (chat {}). Add to allowFrom.",
                sender_id,
                chat_id,
            )
            return

        content_parts = []
        media: list[str] = []

        if event_name == "message.text.received":
            text = msg.get("text", "")
            if text:
                content_parts.append(text)
        elif event_name == "message.image.received":
            photo = msg.get("photo", "")
            caption = msg.get("caption", "")
            if photo:
                media.append(photo)
            if caption:
                content_parts.append(caption)
            if not content_parts:
                content_parts.append("[image]")

        if not content_parts and not media:
            return

        content = "\n".join(content_parts).strip() or "[empty]"

        await self._handle_message(
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media if media else None,
            metadata={
                "message_id": msg.get("message_id"),
                "date": msg.get("date"),
                "event_name": event_name,
                "chat_type": chat_type,
            },
        )

    async def stop(self) -> None:
        """Stop the Zalo channel."""
        self._running = False
        if self._http:
            await self._http.aclose()
            self._http = None

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through Zalo (chunked to 2000 chars)."""
        if not self._http:
            logger.warning("Zalo channel not connected")
            return

        chat_id = msg.chat_id

        # Send media first (images as URLs)
        for media_url in msg.media or []:
            if media_url.startswith(("http://", "https://")):
                try:
                    await self._http.post(
                        self._api_url("sendPhoto"),
                        json={"chat_id": chat_id, "photo": media_url},
                        headers={"Content-Type": "application/json"},
                    )
                except Exception as e:
                    logger.error("Zalo sendPhoto failed: {}", e)
            else:
                logger.warning("Zalo sendPhoto requires URL, got: {}", media_url[:50])

        # Send text in chunks
        if msg.content and msg.content != "[empty message]":
            for chunk in _split_message(msg.content):
                try:
                    resp = await self._http.post(
                        self._api_url("sendMessage"),
                        json={"chat_id": chat_id, "text": chunk},
                        headers={"Content-Type": "application/json"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if not data.get("ok"):
                        logger.warning("Zalo sendMessage failed: {}", data)
                except Exception as e:
                    logger.error("Zalo sendMessage failed: {}", e)
