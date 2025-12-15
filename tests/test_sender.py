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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_digest_markdown_fallback(sample_config, mock_logger):
    """Test markdown parsing error fallback to plain text."""
    from telegram.error import TelegramError

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()

        # First call fails with markdown parsing error
        # Second call succeeds with plain text
        send_message_mock = AsyncMock(
            side_effect=[
                TelegramError("Can't parse entities: can't find end of the entity"),
                None,  # Second call succeeds
            ]
        )
        mock_bot.send_message = send_message_mock
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_digest("Test *invalid markdown", user_id=123456789)

    assert result is True
    # Should be called twice: first with Markdown (fails), then with plain text (succeeds)
    assert send_message_mock.call_count == 2

    # Verify the second call used plain text (parse_mode=None)
    second_call_kwargs = send_message_mock.call_args_list[1][1]
    assert second_call_kwargs.get("parse_mode") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_old_digests_success(sample_config, mock_logger, tmp_path, monkeypatch):
    """Test cleaning up old digest messages."""
    from src.utils import save_digest_message_ids

    # Setup storage
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    # Save some message IDs
    user_id = 123456789
    message_ids = [101, 102, 103]
    save_digest_message_ids(message_ids, user_id)

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.delete_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.cleanup_old_digests(user_id)

    assert result is True
    assert mock_bot.delete_message.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_old_digests_no_messages(sample_config, mock_logger, tmp_path, monkeypatch):
    """Test cleanup when no messages exist."""
    storage_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.cleanup_old_digests(123456789)

    assert result is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_old_digests_unauthorized(sample_config, mock_logger):
    """Test cleanup with unauthorized user."""
    sender = DigestSender(sample_config, mock_logger)
    result = await sender.cleanup_old_digests(999999999)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_channel_messages_success(sample_config, mock_logger):
    """Test sending channel messages."""
    channel_messages = [
        ("Channel 1", "Message 1"),
        ("Channel 2", "Message 2"),
    ]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_channel_messages(channel_messages, user_id=123456789)

    assert result is True
    assert mock_bot.send_message.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_channel_messages_with_failure(sample_config, mock_logger):
    """Test sending channel messages with one failure."""
    from telegram.error import TelegramError

    channel_messages = [
        ("Channel 1", "Message 1"),
        ("Channel 2", "Message 2"),
    ]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        # First call fails, second succeeds
        mock_bot.send_message = AsyncMock(
            side_effect=[TelegramError("API Error"), MagicMock()]
        )
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_channel_messages(channel_messages, user_id=123456789)

    assert result is False  # Not all succeeded
    assert mock_bot.send_message.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_channel_messages_with_tracking(sample_config, mock_logger, tmp_path, monkeypatch):
    """Test sending channel messages with message tracking."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [
        ("Channel 1", "Message 1"),
        ("Channel 2", "Message 2"),
    ]
    summary_message = "Summary of digest"

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()

        # Create mock message objects with message_id
        mock_message1 = MagicMock()
        mock_message1.message_id = 101
        mock_message2 = MagicMock()
        mock_message2.message_id = 102
        mock_message3 = MagicMock()
        mock_message3.message_id = 103

        mock_bot.send_message = AsyncMock(
            side_effect=[mock_message1, mock_message2, mock_message3]
        )
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message=summary_message, user_id=123456789
        )

    assert result is True
    # Should be called 3 times: 2 for channels + 1 for summary
    assert mock_bot.send_message.call_count == 3

    # Verify message IDs were saved
    from src.utils import get_digest_message_ids

    saved_ids = get_digest_message_ids(123456789)
    assert len(saved_ids) == 3
    assert 101 in saved_ids
    assert 102 in saved_ids
    assert 103 in saved_ids


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_channel_messages_with_tracking_no_summary(
    sample_config, mock_logger, tmp_path, monkeypatch
):
    """Test sending channel messages without summary message."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [("Channel 1", "Message 1")]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 101
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message=None, user_id=123456789
        )

    assert result is True
    # Should only send channel message, no summary
    assert mock_bot.send_message.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_channel_messages_long_message(sample_config, mock_logger):
    """Test sending channel message that exceeds length limit."""
    # Create a message longer than 4096 characters
    long_message = "A" * 5000
    channel_messages = [("Channel 1", long_message)]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_channel_messages(channel_messages, user_id=123456789)

    assert result is True
    # Should be called multiple times to send split parts
    assert mock_bot.send_message.call_count > 1
