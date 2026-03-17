"""Zalo Personal (zalouser) channel using Node.js bridge with zca-js.

Requires the Zalo Personal bridge (bridges/zalo) to be running.
Based on OpenClaw's zalouser implementation.
"""

from __future__ import annotations

import asyncio
import json
import os

from loguru import logger

from clawlib.bus import MessageBus, OutboundMessage
from clawlib.channels.base import BaseChannel
from clawlib.config.schema import ZaloUserConfig


class ZaloUserChannel(BaseChannel):
    """
    Zalo Personal channel that connects to a Node.js bridge (zca-js).

    The bridge uses zca-js to handle Zalo Web. Communication between
    Python and Node.js is via WebSocket.
    """

    name = "zalouser"

    def __init__(self, config: ZaloUserConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: ZaloUserConfig = config
        self._ws = None
        self._connected = False
        self._thread_types: dict[str, str] = {}  # threadId -> "user"|"group"

    async def start(self) -> None:
        """Start the Zalo Personal channel by connecting to the bridge."""
        import websockets

        bridge_url = os.environ.get("ZALO_PERSONAL_BRIDGE_URL")
        if not bridge_url:
            port = os.environ.get("ZALO_PERSONAL_BRIDGE_PORT", "3002")
            bridge_url = f"ws://localhost:{port}"

        logger.info("Connecting to Zalo Personal bridge at {}...", bridge_url)

        self._running = True

        while self._running:
            try:
                async with websockets.connect(bridge_url) as ws:
                    self._ws = ws
                    self._connected = True
                    logger.info("Connected to Zalo Personal bridge")

                    async for message in ws:
                        try:
                            await self._handle_bridge_message(message)
                        except Exception as e:
                            logger.error("Error handling bridge message: {}", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                self._ws = None
                logger.warning("Zalo Personal bridge connection error: {}", e)

                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the Zalo Personal channel."""
        self._running = False
        self._connected = False

        if self._ws:
            await self._ws.close()
            self._ws = None

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through Zalo Personal."""
        if not self._ws or not self._connected:
            logger.warning("Zalo Personal bridge not connected")
            return

        thread_type = self._thread_types.get(msg.chat_id, "user")

        try:
            payload = {
                "type": "send",
                "to": msg.chat_id,
                "text": msg.content,
                "threadType": thread_type,
            }
            await self._ws.send(json.dumps(payload))
        except Exception as e:
            logger.error("Error sending Zalo Personal message: {}", e)

    async def _handle_bridge_message(self, raw: str) -> None:
        """Handle a message from the bridge."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from bridge: {}", raw[:100])
            return

        msg_type = data.get("type")

        if msg_type == "message":
            sender = data.get("sender", "")
            thread_id = data.get("threadId", sender)
            thread_type = data.get("threadType", "user")
            if not thread_id:
                logger.warning("Zalo Personal message missing threadId, skipping")
                return

            self._thread_types[thread_id] = thread_type

            if thread_type == "group" and self.config.group_policy == "disabled":
                return
            if thread_type == "group" and self.config.group_policy == "mention":
                content = data.get("content", "")
                if "@" not in content:
                    return

            content = data.get("content", "")
            await self._handle_message(
                sender_id=sender,
                chat_id=thread_id,
                content=content,
                metadata={
                    "message_id": data.get("id"),
                    "timestamp": data.get("timestamp"),
                    "is_group": data.get("isGroup", False),
                    "thread_type": thread_type,
                },
            )

        elif msg_type == "status":
            status = data.get("status")
            logger.info("Zalo Personal status: {}", status)

            if status == "connected":
                self._connected = True
            elif status == "disconnected":
                self._connected = False

        elif msg_type == "qr":
            logger.info("Scan QR code in the bridge terminal to connect Zalo")

        elif msg_type == "error":
            logger.error("Zalo Personal bridge error: {}", data.get("error"))
