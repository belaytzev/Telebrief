"""Tests for sender module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.sender import DigestSender


@pytest.mark.unit
def test_sender_initialization(sample_config, mock_logger):
    """Test sender initialization."""
    sender = DigestSender(sample_config, mock_logger)

    assert sender.config == sample_config
    assert sender.logger == mock_logger
    assert sender.target_user_id == 123456789


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_digest_success(sample_config, mock_logger):
    """Test successful digest sending."""
    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_digest("Test digest", user_id=123456789)

    assert result is True
    assert mock_bot.send_message.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_digest_unauthorized(sample_config, mock_logger):
    """Test sending to unauthorized user."""
    sender = DigestSender(sample_config, mock_logger)

    result = await sender.send_digest("Test digest", user_id=999999999)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_digest_error(sample_config, mock_logger):
    """Test error handling in digest sending."""
    from telegram.error import TelegramError

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=TelegramError("API Error"))
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_digest("Test digest", user_id=123456789)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_long_digest(sample_config, mock_logger):
    """Test sending long digest that needs splitting."""
    # Create a long digest
    long_digest = "A" * 5000

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        send_message_mock = AsyncMock()
        mock_bot.send_message = send_message_mock
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_digest(long_digest, user_id=123456789)

    assert result is True
    # Should be called multiple times for split messages
    assert send_message_mock.call_count > 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_message_success(sample_config, mock_logger):
    """Test sending simple message."""
    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_message("Test message", user_id=123456789)

    assert result is True
    assert mock_bot.send_message.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_message_unauthorized(sample_config, mock_logger):
    """Test sending message to unauthorized user."""
    sender = DigestSender(sample_config, mock_logger)

    result = await sender.send_message("Test message", user_id=999999999)

    assert result is False
