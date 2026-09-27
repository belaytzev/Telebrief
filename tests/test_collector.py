"""Tests for collector module."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collector import MessageCollector


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_channel_messages_passes_search_and_limit(sample_config, mock_logger):
    """search and limit reach Telethon's iter_messages; matches come back as Message objects."""
    with patch("src.collector.TelegramClient"):
        collector = MessageCollector(sample_config, mock_logger)

    now = datetime.now(timezone.utc)
    hit = SimpleNamespace(id=7, date=now, text="kubernetes release", media=None, sender=None)
    seen = {}

    async def iter_messages(entity, **kwargs):
        seen.update(kwargs)
        yield hit

    collector.client = MagicMock()
    collector.client.get_entity = AsyncMock(return_value=SimpleNamespace(username="test", id=1))
    collector.client.iter_messages = iter_messages

    messages = await collector.fetch_channel_messages(
        sample_config.channels[0], now - timedelta(days=1), search="kubernetes", limit=5
    )

    assert seen["search"] == "kubernetes"
    assert seen["limit"] == 5
    assert [m.text for m in messages] == ["kubernetes release"]
    assert messages[0].link == "https://t.me/test/7"
