"""Channel manager for coordinating chat channels."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger

from clawlib.bus import MessageBus
from clawlib.channels.base import BaseChannel
from clawlib.config.schema import Config


class ChannelManager:
    """
    Manages chat channels and coordinates message routing.

    Responsibilities:
    - Initialize enabled channels (Telegram, WhatsApp, etc.)
    - Start/stop channels
    - Route outbound messages
    """

    def __init__(self, config: Config, bus: MessageBus, workspace: Path | None = None):
        self.config = config
        self.bus = bus
        self.workspace = workspace or Path(".")
        self.channels: dict[str, BaseChannel] = {}
        self._dispatch_task: asyncio.Task | None = None

        self._init_channels()

    def _init_channels(self) -> None:
        """Initialize channels based on config.

        Channels are only added when enabled AND have required credentials.
        This avoids "Starting X channel..." followed by "token not configured".
        """

        # Telegram channel (requires token)
        if self.config.channels.telegram.enabled and self.config.channels.telegram.token:
            try:
                from clawlib.channels.telegram import TelegramChannel

                self.channels["telegram"] = TelegramChannel(
                    self.config.channels.telegram,
                    self.bus,
                    groq_api_key=self.config.providers.groq.api_key,
                    workspace=self.workspace,
                )
                logger.info("Telegram channel enabled")
            except ImportError as e:
                logger.warning("Telegram channel not available: {}", e)
        elif self.config.channels.telegram.enabled:
            logger.warning(
                "Telegram enabled but token not configured. Set token in Channels settings, save, then restart."
            )

        # WhatsApp channel
        if self.config.channels.whatsapp.enabled:
            try:
                from clawlib.channels.whatsapp import WhatsAppChannel

                self.channels["whatsapp"] = WhatsAppChannel(self.config.channels.whatsapp, self.bus)
                logger.info("WhatsApp channel enabled")
            except ImportError as e:
                logger.warning("WhatsApp channel not available: {}", e)

        # Discord channel
        if self.config.channels.discord.enabled:
            try:
                from clawlib.channels.discord import DiscordChannel

                self.channels["discord"] = DiscordChannel(
                    self.config.channels.discord,
                    self.bus,
                    workspace=self.workspace,
                )
                logger.info("Discord channel enabled")
            except ImportError as e:
                logger.warning("Discord channel not available: {}", e)

        # Feishu channel
        if self.config.channels.feishu.enabled:
            try:
                from clawlib.channels.feishu import FeishuChannel

                self.channels["feishu"] = FeishuChannel(self.config.channels.feishu, self.bus)
                logger.info("Feishu channel enabled")
            except ImportError as e:
                logger.warning("Feishu channel not available: {}", e)

        # Email channel
        if self.config.channels.email.enabled:
            try:
                from clawlib.channels.email import EmailChannel

                self.channels["email"] = EmailChannel(self.config.channels.email, self.bus)
                logger.info("Email channel enabled")
            except ImportError as e:
                logger.warning("Email channel not available: {}", e)

        # Zalo channel (Bot API, long-polling)
        if self.config.channels.zalo.enabled and self.config.channels.zalo.bot_token:
            try:
                from clawlib.channels.zalo import ZaloChannel

                self.channels["zalo"] = ZaloChannel(
                    self.config.channels.zalo,
                    self.bus,
                    workspace=self.workspace,
                )
                logger.info("Zalo channel enabled")
            except ImportError as e:
                logger.warning("Zalo channel not available: {}", e)
        elif self.config.channels.zalo.enabled:
            logger.warning(
                "Zalo enabled but bot_token not configured. Set botToken in Channels settings, save, then restart."
            )

        # Zalo Personal (zalouser) channel — requires Node.js bridge (bridges/zalo)
        if self.config.channels.zalouser.enabled:
            try:
                from clawlib.channels.zalouser import ZaloUserChannel

                self.channels["zalouser"] = ZaloUserChannel(
                    self.config.channels.zalouser,
                    self.bus,
                )
                logger.info("Zalo Personal (zalouser) channel enabled")
            except ImportError as e:
                logger.warning("Zalo Personal channel not available: {}", e)

        # Microsoft Teams channel (Bot Framework, webhook-based)
        if (
            self.config.channels.teams.enabled
            and self.config.channels.teams.app_id
            and self.config.channels.teams.app_password
        ):
            try:
                from clawlib.channels.teams import TeamsChannel

                self.channels["teams"] = TeamsChannel(
                    self.config.channels.teams,
                    self.bus,
                    workspace=self.workspace,
                )
                logger.info("Teams channel enabled")
            except ImportError as e:
                logger.warning("Teams channel not available: {}", e)
        elif self.config.channels.teams.enabled:
            logger.warning(
                "Teams enabled but app_id or app_password not configured. "
                "Set in Channels settings, save, then restart."
            )

        # Slack channel (socket mode requires bot_token and app_token)
        slack_ready = (
            self.config.channels.slack.enabled
            and self.config.channels.slack.bot_token
            and self.config.channels.slack.app_token
        )
        if slack_ready:
            try:
                from clawlib.channels.slack import SlackChannel

                self.channels["slack"] = SlackChannel(self.config.channels.slack, self.bus)
                logger.info("Slack channel enabled")
            except ImportError as e:
                logger.warning("Slack channel not available: {}", e)
        elif self.config.channels.slack.enabled:
            logger.warning(
                "Slack enabled but bot_token or app_token not configured. Set in Channels settings, save, then restart."
            )

    async def _start_channel(self, name: str, channel: BaseChannel) -> None:
        """Start a channel and log any exceptions."""
        try:
            await channel.start()
        except Exception as e:
            logger.error("Failed to start channel {}: {}", name, e)

    async def start_all(self) -> None:
        """Start all channels and the outbound dispatcher."""
        if not self.channels:
            logger.warning("No channels enabled")
            return

        # Start outbound dispatcher
        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())

        # Start channels
        tasks = []
        for name, channel in self.channels.items():
            logger.info("Starting {} channel...", name)
            tasks.append(asyncio.create_task(self._start_channel(name, channel)))

        # Wait for all to complete (they should run forever)
        await asyncio.gather(*tasks, return_exceptions=True)

    def set_config(self, config: Config) -> None:
        """Update config and re-initialize channel instances (call after stop_all() before start_all())."""
        self.config = config
        self.channels.clear()
        self._init_channels()
        self._stopped = False

    async def stop_all(self) -> None:
        """Stop all channels and the dispatcher (idempotent)."""
        if getattr(self, "_stopped", False):
            return
        self._stopped = True
        logger.info("Stopping all channels...")

        # Stop dispatcher
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        # Stop all channels
        for name, channel in self.channels.items():
            try:
                await asyncio.wait_for(channel.stop(), timeout=5.0)
                logger.info("Stopped {} channel", name)
            except asyncio.CancelledError:
                logger.debug("Channel {} stop cancelled during shutdown", name)
            except asyncio.TimeoutError:
                logger.warning("Channel {} stop timed out", name)
            except Exception as e:
                logger.error("Error stopping {}: {}", name, e)

    async def _dispatch_outbound(self) -> None:
        """Dispatch outbound messages to the appropriate channel."""
        logger.info("Outbound dispatcher started")

        while True:
            try:
                msg = await asyncio.wait_for(self.bus.consume_outbound(), timeout=1.0)

                channel = self.channels.get(msg.channel)
                if channel:
                    try:
                        await channel.send(msg)
                    except Exception as e:
                        logger.error("Error sending to {}: {}", msg.channel, e)
                else:
                    logger.warning("Unknown channel: {}", msg.channel)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def get_channel(self, name: str) -> BaseChannel | None:
        """Get a channel by name."""
        return self.channels.get(name)

    def get_status(self) -> dict[str, Any]:
        """Get status of all channels."""
        return {
            name: {"enabled": True, "running": channel.is_running}
            for name, channel in self.channels.items()
        }

    @property
    def enabled_channels(self) -> list[str]:
        """Get list of enabled channel names."""
        return list(self.channels.keys())
