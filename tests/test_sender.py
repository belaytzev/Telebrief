"""Tests for sender module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import InlineKeyboardMarkup

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
        mock_bot.send_message = AsyncMock(side_effect=[TelegramError("API Error"), MagicMock()])
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_channel_messages(channel_messages, user_id=123456789)

    assert result is False  # Not all succeeded
    assert mock_bot.send_message.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_channel_messages_with_tracking(
    sample_config, mock_logger, tmp_path, monkeypatch
):
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

        mock_bot.send_message = AsyncMock(side_effect=[mock_message1, mock_message2, mock_message3])
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
async def test_send_channel_messages_loop_channel_id_map(sample_config, mock_logger):
    """Test that _send_channel_messages_loop returns correct channel_id_map."""
    channel_messages = [
        ("Channel A", "Message A"),
        ("Channel B", "Message B"),
    ]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()

        mock_msg_a = MagicMock()
        mock_msg_a.message_id = 201
        mock_msg_b = MagicMock()
        mock_msg_b.message_id = 202

        mock_bot.send_message = AsyncMock(side_effect=[mock_msg_a, mock_msg_b])
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        sent_ids, channel_id_map, success_count, failed_channels = (
            await sender._send_channel_messages_loop(123456789, channel_messages)
        )

    assert sent_ids == [201, 202]
    assert channel_id_map == [("Channel A", 201), ("Channel B", 202)]
    assert success_count == 2
    assert failed_channels == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_channel_messages_loop_channel_id_map_with_failure(sample_config, mock_logger):
    """Test that channel_id_map only contains successful sends."""
    from telegram.error import TelegramError

    channel_messages = [
        ("Channel A", "Message A"),
        ("Channel B", "Message B"),
    ]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()

        mock_msg_a = MagicMock()
        mock_msg_a.message_id = 201

        mock_bot.send_message = AsyncMock(side_effect=[mock_msg_a, TelegramError("API Error")])
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        sent_ids, channel_id_map, success_count, failed_channels = (
            await sender._send_channel_messages_loop(123456789, channel_messages)
        )

    assert sent_ids == [201]
    assert channel_id_map == [("Channel A", 201)]
    assert success_count == 1
    assert failed_channels == ["Channel B"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summary_message_sent_with_toc_keyboard(
    sample_config, mock_logger, tmp_path, monkeypatch
):
    """Test that summary message includes a TOC keyboard when channels are sent successfully."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [
        ("Channel 1", "Message 1"),
        ("Channel 2", "Message 2"),
    ]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()

        mock_msg1 = MagicMock()
        mock_msg1.message_id = 101
        mock_msg2 = MagicMock()
        mock_msg2.message_id = 102
        mock_summary_msg = MagicMock()
        mock_summary_msg.message_id = 103

        mock_bot.send_message = AsyncMock(side_effect=[mock_msg1, mock_msg2, mock_summary_msg])
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    # The 3rd send_message call is the summary and should carry reply_markup
    summary_call_kwargs = mock_bot.send_message.call_args_list[2][1]
    markup = summary_call_kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    assert len(markup.inline_keyboard) == 2
    assert "message_id=101" in markup.inline_keyboard[0][0].url
    assert "message_id=102" in markup.inline_keyboard[1][0].url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toc_keyboard_uses_bot_id_not_user_id_for_private_chat(
    mock_logger, tmp_path, monkeypatch
):
    """Test that TOC deep links use the bot's ID (not the user's ID) for private chats.

    Uses a config where bot_id != target_user_id to verify the substitution.
    """
    from src.config_loader import ChannelConfig, Config, Settings

    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    # bot_id (555000) is distinct from target_user_id (123456789)
    settings = Settings(
        schedule_time="08:00",
        timezone="UTC",
        lookback_hours=24,
        openai_model="gpt-5-nano",
        openai_temperature=0.7,
        temperature=0.7,
        max_tokens_per_summary=1500,
        use_emojis=True,
        include_statistics=True,
        target_user_id=123456789,
        auto_cleanup_old_digests=True,
        max_messages_per_channel=500,
        max_prompt_chars=8000,
        api_timeout=30,
        ai_provider="openai",
        ai_model="gpt-5-nano",
        ollama_base_url="http://localhost:11434",
        output_language="Russian",
    )
    config = Config(
        channels=[ChannelConfig(id="@test_channel", name="Test Channel")],
        settings=settings,
        telegram_api_id=12345678,
        telegram_api_hash="test_hash",
        telegram_bot_token="555000:BOT-TOKEN",
        openai_api_key="sk-test-key",
        log_level="INFO",
        anthropic_api_key="",
    )

    channel_messages = [("Channel 1", "Message 1")]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_msg1 = MagicMock()
        mock_msg1.message_id = 101
        mock_summary_msg = MagicMock()
        mock_summary_msg.message_id = 102
        mock_bot.send_message = AsyncMock(side_effect=[mock_msg1, mock_summary_msg])
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(config, mock_logger)
        # user_id=123456789 is positive (private chat), so bot_id=555000 should be used
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    summary_call_kwargs = mock_bot.send_message.call_args_list[1][1]
    markup = summary_call_kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    btn_url = markup.inline_keyboard[0][0].url
    # Must use bot_id (555000), NOT the recipient user_id (123456789)
    assert "user_id=555000" in btn_url
    assert "user_id=123456789" not in btn_url
    assert "message_id=101" in btn_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summary_message_sent_without_toc_keyboard_when_all_fail(
    sample_config, mock_logger, tmp_path, monkeypatch
):
    """Test that summary message is not sent when all channel sends fail (success_count == 0)."""
    from telegram.error import TelegramError

    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [("Channel 1", "Message 1")]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=TelegramError("API Error"))
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    # Only the failed channel attempt; summary is never called (success_count == 0)
    assert mock_bot.send_message.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summary_toc_keyboard_contains_only_successful_channels(
    sample_config, mock_logger, tmp_path, monkeypatch
):
    """Test that TOC keyboard only includes channels that were sent successfully."""
    from telegram.error import TelegramError

    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [
        ("Channel 1", "Message 1"),
        ("Channel 2", "Message 2"),
    ]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()

        mock_msg1 = MagicMock()
        mock_msg1.message_id = 101
        mock_summary_msg = MagicMock()
        mock_summary_msg.message_id = 103

        # Channel 1 succeeds, Channel 2 fails, then summary is sent
        mock_bot.send_message = AsyncMock(
            side_effect=[mock_msg1, TelegramError("API Error"), mock_summary_msg]
        )
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    # Summary is the 3rd call (index 2)
    summary_call_kwargs = mock_bot.send_message.call_args_list[2][1]
    markup = summary_call_kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    # Only Channel 1 succeeded, so keyboard has exactly one button
    assert len(markup.inline_keyboard) == 1
    assert "message_id=101" in markup.inline_keyboard[0][0].url


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
