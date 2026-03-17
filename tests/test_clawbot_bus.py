"""Tests for clawbot.core.bus module."""

import asyncio
from datetime import datetime

import pytest

from clawlib.bus import InboundMessage, MessageBus, OutboundMessage


class TestInboundMessage:
    """Tests for InboundMessage dataclass."""

    def test_create_basic(self):
        """InboundMessage should create with required fields."""
        msg = InboundMessage(
            channel="telegram",
            sender_id="user123",
            chat_id="chat456",
            content="Hello",
        )
        assert msg.channel == "telegram"
        assert msg.sender_id == "user123"
        assert msg.chat_id == "chat456"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.media == []
        assert msg.metadata == {}

    def test_create_with_media(self):
        """InboundMessage should accept media list."""
        msg = InboundMessage(
            channel="whatsapp",
            sender_id="user",
            chat_id="chat",
            content="Image",
            media=["https://example.com/image.jpg"],
        )
        assert msg.media == ["https://example.com/image.jpg"]

    def test_create_with_metadata(self):
        """InboundMessage should accept metadata dict."""
        msg = InboundMessage(
            channel="slack",
            sender_id="U123",
            chat_id="C456",
            content="Test",
            metadata={"thread_ts": "123.456"},
        )
        assert msg.metadata == {"thread_ts": "123.456"}

    def test_session_key(self):
        """session_key property should combine channel and chat_id."""
        msg = InboundMessage(
            channel="telegram",
            sender_id="user",
            chat_id="12345",
            content="Test",
        )
        assert msg.session_key == "telegram:12345"


class TestOutboundMessage:
    """Tests for OutboundMessage dataclass."""

    def test_create_basic(self):
        """OutboundMessage should create with required fields."""
        msg = OutboundMessage(
            channel="telegram",
            chat_id="12345",
            content="Hello back!",
        )
        assert msg.channel == "telegram"
        assert msg.chat_id == "12345"
        assert msg.content == "Hello back!"
        assert msg.reply_to is None
        assert msg.media == []
        assert msg.metadata == {}

    def test_create_with_reply(self):
        """OutboundMessage should accept reply_to."""
        msg = OutboundMessage(
            channel="telegram",
            chat_id="12345",
            content="Reply",
            reply_to="msg_789",
        )
        assert msg.reply_to == "msg_789"


class TestMessageBus:
    """Tests for MessageBus."""

    def test_init(self):
        """MessageBus should initialize with empty queues."""
        bus = MessageBus()
        assert bus.inbound_size == 0
        assert bus.outbound_size == 0
        assert bus._running is False

    @pytest.mark.asyncio
    async def test_publish_inbound(self):
        """publish_inbound should add message to inbound queue."""
        bus = MessageBus()
        msg = InboundMessage(
            channel="test",
            sender_id="user",
            chat_id="chat",
            content="Hello",
        )
        await bus.publish_inbound(msg)
        assert bus.inbound_size == 1

    @pytest.mark.asyncio
    async def test_consume_inbound(self):
        """consume_inbound should retrieve message from queue."""
        bus = MessageBus()
        msg = InboundMessage(
            channel="test",
            sender_id="user",
            chat_id="chat",
            content="Hello",
        )
        await bus.publish_inbound(msg)
        received = await bus.consume_inbound()
        assert received == msg
        assert bus.inbound_size == 0

    @pytest.mark.asyncio
    async def test_publish_outbound(self):
        """publish_outbound should add message to outbound queue."""
        bus = MessageBus()
        msg = OutboundMessage(
            channel="test",
            chat_id="chat",
            content="Response",
        )
        await bus.publish_outbound(msg)
        assert bus.outbound_size == 1

    @pytest.mark.asyncio
    async def test_consume_outbound(self):
        """consume_outbound should retrieve message from queue."""
        bus = MessageBus()
        msg = OutboundMessage(
            channel="test",
            chat_id="chat",
            content="Response",
        )
        await bus.publish_outbound(msg)
        received = await bus.consume_outbound()
        assert received == msg
        assert bus.outbound_size == 0

    @pytest.mark.asyncio
    async def test_subscribe_outbound(self):
        """subscribe_outbound should register callback for channel."""
        bus = MessageBus()
        received = []

        async def callback(msg: OutboundMessage) -> None:
            received.append(msg)

        bus.subscribe_outbound("test", callback)
        assert "test" in bus._outbound_subscribers
        assert callback in bus._outbound_subscribers["test"]

    @pytest.mark.asyncio
    async def test_dispatch_outbound(self):
        """dispatch_outbound should call subscribers for matching channel."""
        bus = MessageBus()
        received = []

        async def callback(msg: OutboundMessage) -> None:
            received.append(msg)

        bus.subscribe_outbound("test", callback)

        msg = OutboundMessage(channel="test", chat_id="chat", content="Hello")
        await bus.publish_outbound(msg)

        dispatch_task = asyncio.create_task(bus.dispatch_outbound())

        await asyncio.sleep(0.1)
        bus.stop()
        await asyncio.sleep(0.1)
        dispatch_task.cancel()

        assert len(received) == 1
        assert received[0] == msg

    @pytest.mark.asyncio
    async def test_dispatch_outbound_no_subscriber(self):
        """dispatch_outbound should not fail when no subscribers."""
        bus = MessageBus()

        msg = OutboundMessage(channel="unknown", chat_id="chat", content="Hello")
        await bus.publish_outbound(msg)

        dispatch_task = asyncio.create_task(bus.dispatch_outbound())
        await asyncio.sleep(0.1)
        bus.stop()
        dispatch_task.cancel()

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_channel(self):
        """Multiple subscribers for same channel should all receive messages."""
        bus = MessageBus()
        received1, received2 = [], []

        async def callback1(msg: OutboundMessage) -> None:
            received1.append(msg)

        async def callback2(msg: OutboundMessage) -> None:
            received2.append(msg)

        bus.subscribe_outbound("test", callback1)
        bus.subscribe_outbound("test", callback2)

        msg = OutboundMessage(channel="test", chat_id="chat", content="Hello")
        await bus.publish_outbound(msg)

        dispatch_task = asyncio.create_task(bus.dispatch_outbound())
        await asyncio.sleep(0.1)
        bus.stop()
        dispatch_task.cancel()

        assert len(received1) == 1
        assert len(received2) == 1

    def test_stop(self):
        """stop() should set _running to False."""
        bus = MessageBus()
        bus._running = True
        bus.stop()
        assert bus._running is False

    @pytest.mark.asyncio
    async def test_fifo_ordering(self):
        """Messages should be consumed in FIFO order."""
        bus = MessageBus()
        for i in range(3):
            await bus.publish_inbound(
                InboundMessage(
                    channel="test",
                    sender_id="user",
                    chat_id="chat",
                    content=f"msg-{i}",
                )
            )

        for i in range(3):
            msg = await bus.consume_inbound()
            assert msg.content == f"msg-{i}"
