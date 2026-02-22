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

        # Summary placeholder sent first (id=101), then channels (102, 103)
        mock_message1 = MagicMock()
        mock_message1.message_id = 101
        mock_message2 = MagicMock()
        mock_message2.message_id = 102
        mock_message3 = MagicMock()
        mock_message3.message_id = 103

        mock_bot.send_message = AsyncMock(side_effect=[mock_message1, mock_message2, mock_message3])
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        result = await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message=summary_message, user_id=123456789
        )

    assert result is True
    # 3 send_message calls: 1 for summary placeholder + 2 for channels
    assert mock_bot.send_message.call_count == 3
    # TOC keyboard added via edit after channels are sent
    assert mock_bot.edit_message_reply_markup.call_count == 1

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
    """Test that summary is sent first (no keyboard), then TOC keyboard added via edit after channels."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [
        ("Channel 1", "Message 1"),
        ("Channel 2", "Message 2"),
    ]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()

        # Summary placeholder first (id=103), then channels (101, 102)
        mock_summary_msg = MagicMock()
        mock_summary_msg.message_id = 103
        mock_msg1 = MagicMock()
        mock_msg1.message_id = 101
        mock_msg2 = MagicMock()
        mock_msg2.message_id = 102

        mock_bot.send_message = AsyncMock(side_effect=[mock_summary_msg, mock_msg1, mock_msg2])
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    # First send_message call is the summary placeholder — must have NO keyboard
    first_call_kwargs = mock_bot.send_message.call_args_list[0][1]
    assert first_call_kwargs.get("reply_markup") is None

    # TOC keyboard attached via edit_message_reply_markup after channels are sent
    assert mock_bot.edit_message_reply_markup.call_count == 1
    edit_kwargs = mock_bot.edit_message_reply_markup.call_args[1]
    markup = edit_kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    assert len(markup.inline_keyboard) == 2
    # Private chat: URL uses bot_id (peer from human's perspective). sample_config token
    # "123456789:ABC-DEF" → bot_id=123456789 (coincides with user_id in this test).
    assert markup.inline_keyboard[0][0].url == "tg://openmessage?user_id=123456789&message_id=101"
    assert markup.inline_keyboard[1][0].url == "tg://openmessage?user_id=123456789&message_id=102"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toc_keyboard_uses_bot_id_for_private_chat(mock_logger, tmp_path, monkeypatch):
    """Test that TOC buttons for private chats use bot_id (not recipient's ID) in tg://openmessage URL for navigation without copy."""
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
        # Summary placeholder sent first (id=102), then channel (id=101)
        mock_summary_msg = MagicMock()
        mock_summary_msg.message_id = 102
        mock_msg1 = MagicMock()
        mock_msg1.message_id = 101
        mock_bot.send_message = AsyncMock(side_effect=[mock_summary_msg, mock_msg1])
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(config, mock_logger)
        # user_id=123456789 is positive (private chat), so user_id is embedded in callback_data
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    # TOC keyboard added via edit_message_reply_markup, not in the send call
    assert mock_bot.edit_message_reply_markup.call_count == 1
    edit_kwargs = mock_bot.edit_message_reply_markup.call_args[1]
    markup = edit_kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    btn = markup.inline_keyboard[0][0]
    # Private chat: tg://openmessage user_id must be the bot's ID (peer from human's perspective),
    # not the recipient's own ID. Bot token "555000:BOT-TOKEN" → bot_id=555000.
    assert btn.callback_data is None
    assert btn.url == "tg://openmessage?user_id=555000&message_id=101"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_toc_keyboard_not_edited_when_all_channels_fail(
    sample_config, mock_logger, tmp_path, monkeypatch
):
    """Test that TOC keyboard is not edited onto summary when all channel sends fail."""
    from telegram.error import TelegramError

    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [("Channel 1", "Message 1")]

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_summary = MagicMock()
        mock_summary.message_id = 100
        # Summary placeholder succeeds; channel fails
        mock_bot.send_message = AsyncMock(side_effect=[mock_summary, TelegramError("API Error")])
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_bot.delete_message = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    # 2 send_message calls: summary placeholder + failed channel attempt
    assert mock_bot.send_message.call_count == 2
    # edit_message_reply_markup must NOT be called (no successful channels = no TOC)
    assert mock_bot.edit_message_reply_markup.call_count == 0
    # Orphaned summary placeholder must be deleted
    mock_bot.delete_message.assert_called_once_with(chat_id=123456789, message_id=100)


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

        # Summary placeholder first (id=103), then ch1 succeeds (id=101), ch2 fails
        mock_summary_msg = MagicMock()
        mock_summary_msg.message_id = 103
        mock_msg1 = MagicMock()
        mock_msg1.message_id = 101

        mock_bot.send_message = AsyncMock(
            side_effect=[mock_summary_msg, mock_msg1, TelegramError("API Error")]
        )
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message="Summary", user_id=123456789
        )

    # TOC keyboard added via edit — only Channel 1 succeeded
    assert mock_bot.edit_message_reply_markup.call_count == 1
    edit_kwargs = mock_bot.edit_message_reply_markup.call_args[1]
    markup = edit_kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    # Only Channel 1 succeeded, so keyboard has exactly one button
    assert len(markup.inline_keyboard) == 1
    # Private chat: URL uses bot_id. sample_config token "123456789:ABC-DEF" → bot_id=123456789.
    assert markup.inline_keyboard[0][0].url == "tg://openmessage?user_id=123456789&message_id=101"


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summary_sent_before_channel_messages(
    sample_config, mock_logger, tmp_path, monkeypatch
):
    """Test that the summary/TOC placeholder is sent FIRST, before any channel messages."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [("Channel 1", "Message 1"), ("Channel 2", "Message 2")]
    summary_message = "Summary text"

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_summary = MagicMock()
        mock_summary.message_id = 100
        mock_ch1 = MagicMock()
        mock_ch1.message_id = 101
        mock_ch2 = MagicMock()
        mock_ch2.message_id = 102

        mock_bot.send_message = AsyncMock(side_effect=[mock_summary, mock_ch1, mock_ch2])
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message=summary_message, user_id=123456789
        )

    # First send_message call must be the summary placeholder (no reply_markup)
    first_call_kwargs = mock_bot.send_message.call_args_list[0][1]
    assert first_call_kwargs.get("text") == summary_message
    assert first_call_kwargs.get("reply_markup") is None

    # Second and third calls must be the channel messages
    second_call_kwargs = mock_bot.send_message.call_args_list[1][1]
    assert second_call_kwargs.get("text") == "Message 1"

    third_call_kwargs = mock_bot.send_message.call_args_list[2][1]
    assert third_call_kwargs.get("text") == "Message 2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summary_keyboard_edited_with_toc_after_channels(
    sample_config, mock_logger, tmp_path, monkeypatch
):
    """Test that TOC keyboard is added to the summary via edit_message_reply_markup after channels sent."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    channel_messages = [("Channel 1", "Message 1"), ("Channel 2", "Message 2")]
    summary_message = "Summary text"

    with patch("src.sender.Bot") as mock_bot_class:
        mock_bot = MagicMock()
        mock_summary = MagicMock()
        mock_summary.message_id = 100
        mock_ch1 = MagicMock()
        mock_ch1.message_id = 101
        mock_ch2 = MagicMock()
        mock_ch2.message_id = 102

        mock_bot.send_message = AsyncMock(side_effect=[mock_summary, mock_ch1, mock_ch2])
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_bot_class.return_value = mock_bot

        sender = DigestSender(sample_config, mock_logger)
        await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message=summary_message, user_id=123456789
        )

    # edit_message_reply_markup called exactly once, with the summary's message_id
    assert mock_bot.edit_message_reply_markup.call_count == 1
    edit_kwargs = mock_bot.edit_message_reply_markup.call_args[1]
    assert edit_kwargs["chat_id"] == 123456789
    assert edit_kwargs["message_id"] == 100  # summary placeholder id

    markup = edit_kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    assert len(markup.inline_keyboard) == 2
    # Private chat: URL uses bot_id. sample_config token "123456789:ABC-DEF" → bot_id=123456789.
    assert markup.inline_keyboard[0][0].url == "tg://openmessage?user_id=123456789&message_id=101"
    assert markup.inline_keyboard[1][0].url == "tg://openmessage?user_id=123456789&message_id=102"
