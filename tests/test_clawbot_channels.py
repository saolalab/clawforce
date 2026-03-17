"""Tests for channels module (now in clawlib.channels)."""

from pathlib import Path

import pytest

from clawlib.bus import MessageBus, OutboundMessage
from clawlib.channels.base import BaseChannel


class MockConfig:
    """Mock channel configuration."""

    def __init__(self, allow_from=None):
        self.allow_from = allow_from or []


class MockChannel(BaseChannel):
    """Mock channel implementation for testing."""

    name = "mock"

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        pass


class TestBaseChannel:
    """Tests for BaseChannel abstract base class."""

    def test_cannot_instantiate_directly(self):
        """BaseChannel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseChannel(config=None, bus=None)

    def test_init(self):
        """MockChannel should initialize correctly."""
        bus = MessageBus()
        config = MockConfig()
        workspace = Path("/tmp/workspace")
        channel = MockChannel(config=config, bus=bus, workspace=workspace)

        assert channel.config == config
        assert channel.bus == bus
        assert channel.workspace == workspace
        assert channel._running is False

    def test_init_default_workspace(self):
        """Channel should use current dir as default workspace."""
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)
        assert channel.workspace == Path(".")

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Channel should start and stop correctly."""
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)

        assert channel.is_running is False
        await channel.start()
        assert channel.is_running is True
        await channel.stop()
        assert channel.is_running is False


class TestChannelAllowList:
    """Tests for BaseChannel.is_allowed method."""

    def test_empty_allow_list(self):
        """Empty allow list should allow everyone."""
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(allow_from=[]), bus=bus)
        assert channel.is_allowed("any_user") is True
        assert channel.is_allowed("another_user") is True

    def test_allow_list_exact_match(self):
        """User in allow list should be allowed."""
        bus = MessageBus()
        channel = MockChannel(
            config=MockConfig(allow_from=["user1", "user2"]),
            bus=bus,
        )
        assert channel.is_allowed("user1") is True
        assert channel.is_allowed("user2") is True
        assert channel.is_allowed("user3") is False

    def test_allow_list_string_conversion(self):
        """Sender ID should be converted to string."""
        bus = MessageBus()
        channel = MockChannel(
            config=MockConfig(allow_from=["12345"]),
            bus=bus,
        )
        assert channel.is_allowed(12345) is True

    def test_allow_list_pipe_separated(self):
        """Pipe-separated IDs should be checked individually."""
        bus = MessageBus()
        channel = MockChannel(
            config=MockConfig(allow_from=["allowed"]),
            bus=bus,
        )
        assert channel.is_allowed("denied|allowed|other") is True
        assert channel.is_allowed("denied|other") is False


class TestHandleMessage:
    """Tests for BaseChannel._handle_message method."""

    @pytest.mark.asyncio
    async def test_allowed_sender(self):
        """Allowed sender's message should be published to bus."""
        bus = MessageBus()
        channel = MockChannel(
            config=MockConfig(allow_from=["user1"]),
            bus=bus,
        )

        await channel._handle_message(
            sender_id="user1",
            chat_id="chat1",
            content="Hello",
        )

        assert bus.inbound_size == 1
        msg = await bus.consume_inbound()
        assert msg.channel == "mock"
        assert msg.sender_id == "user1"
        assert msg.chat_id == "chat1"
        assert msg.content == "Hello"

    @pytest.mark.asyncio
    async def test_denied_sender(self):
        """Denied sender's message should not be published."""
        bus = MessageBus()
        channel = MockChannel(
            config=MockConfig(allow_from=["allowed"]),
            bus=bus,
        )

        await channel._handle_message(
            sender_id="denied",
            chat_id="chat1",
            content="Hello",
        )

        assert bus.inbound_size == 0

    @pytest.mark.asyncio
    async def test_allowed_chat_id(self):
        """Message from allowed chat_id should be published even if sender not in list."""
        bus = MessageBus()
        channel = MockChannel(
            config=MockConfig(allow_from=["allowed_chat"]),
            bus=bus,
        )

        await channel._handle_message(
            sender_id="any_sender",
            chat_id="allowed_chat",
            content="Hello",
        )

        assert bus.inbound_size == 1

    @pytest.mark.asyncio
    async def test_with_media(self):
        """Message with media should include media list."""
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)

        await channel._handle_message(
            sender_id="user",
            chat_id="chat",
            content="Image",
            media=["https://example.com/image.jpg"],
        )

        msg = await bus.consume_inbound()
        assert msg.media == ["https://example.com/image.jpg"]

    @pytest.mark.asyncio
    async def test_with_metadata(self):
        """Message with metadata should include metadata dict."""
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)

        await channel._handle_message(
            sender_id="user",
            chat_id="chat",
            content="Test",
            metadata={"thread_id": "123"},
        )

        msg = await bus.consume_inbound()
        assert msg.metadata == {"thread_id": "123"}

    @pytest.mark.asyncio
    async def test_empty_allow_list_allows_all(self):
        """Empty allow list should allow all senders."""
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(allow_from=[]), bus=bus)

        await channel._handle_message(
            sender_id="anyone",
            chat_id="any_chat",
            content="Hello",
        )

        assert bus.inbound_size == 1
