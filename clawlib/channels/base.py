"""Base channel interface for chat platforms."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from loguru import logger

from clawlib.bus import InboundMessage, MessageBus, OutboundMessage


class BaseChannel(ABC):
    """
    Abstract base class for chat channel implementations.

    Each channel (Telegram, Discord, etc.) should implement this interface
    to integrate with the message bus.
    """

    name: str = "base"

    def __init__(self, config: Any, bus: MessageBus, workspace: Path | None = None):
        self.config = config
        self.bus = bus
        self.workspace = workspace or Path(".")
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """
        Start the channel and begin listening for messages.

        This should be a long-running async task that:
        1. Connects to the chat platform
        2. Listens for incoming messages
        3. Forwards messages to the bus via _handle_message()
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""
        pass

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through this channel."""
        pass

    def is_allowed(self, sender_id: str) -> bool:
        """Check if a sender is allowed to use this bot."""
        allow_list = getattr(self.config, "allow_from", [])

        if not allow_list:
            return True

        sender_str = str(sender_id)
        if sender_str in allow_list:
            return True
        if "|" in sender_str:
            for part in sender_str.split("|"):
                if part and part in allow_list:
                    return True
        return False

    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Handle an incoming message from the chat platform.

        This method checks permissions and forwards to the bus.
        """
        if not self.is_allowed(sender_id) and not self.is_allowed(chat_id):
            logger.warning(
                f"Access denied for sender {sender_id} (chat {chat_id}) on channel {self.name}. "
                f"Add sender ID, username, or chat/group ID to allowFrom in config."
            )
            return

        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=metadata or {},
        )

        await self.bus.publish_inbound(msg)

    @property
    def is_running(self) -> bool:
        """Check if the channel is running."""
        return self._running
