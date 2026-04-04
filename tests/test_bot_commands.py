"""Tests for bot_commands module — language / output_language coverage and rate limiting."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot_commands import BotCommandHandler


@pytest.fixture
def english_config(sample_config):
    """sample_config with output_language set to English."""
    sample_config.settings.output_language = "English"
    return sample_config


def _make_update(user_id: int):
    """Return a minimal mock Update with an authorized user."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


# ---------------------------------------------------------------------------
# setup_bot_menu
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_bot_menu_uses_output_language(english_config, mock_logger):
    """setup_bot_menu command descriptions respect output_language."""
    handler = BotCommandHandler(english_config, mock_logger)
    mock_app = MagicMock()
    mock_app.bot.set_my_commands = AsyncMock()
    handler.app = mock_app

    await handler.setup_bot_menu()

    commands = mock_app.bot.set_my_commands.call_args[0][0]
    descriptions = [cmd.description for cmd in commands]
    joined = " ".join(descriptions)

    assert "Start the bot" in descriptions
    assert "Generate digest for 24 hours" in descriptions
    assert "Delete old digests" in descriptions
    # No Russian
    assert "Начать" not in joined
    assert "Сгенерировать" not in joined


# ---------------------------------------------------------------------------
# handle_digest
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_digest_processing_message_uses_output_language(english_config, mock_logger):
    """handle_digest sends an English processing message when output_language=English."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with patch(
        "src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=True)
    ):
        await handler.handle_digest(update, MagicMock())

    processing_text = update.message.reply_text.call_args_list[0][0][0]
    assert "Generating digest" in processing_text
    assert "Генерирую" not in processing_text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_digest_success_message_uses_output_language(english_config, mock_logger):
    """handle_digest sends an English success message when digest generation succeeds."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with patch(
        "src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=True)
    ):
        await handler.handle_digest(update, MagicMock())

    success_text = update.message.reply_text.call_args_list[1][0][0]
    assert "Digest ready" in success_text
    assert "Дайджест готов" not in success_text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_digest_error_message_uses_output_language(english_config, mock_logger):
    """handle_digest sends an English error message when generation returns False."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with patch(
        "src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=False)
    ):
        await handler.handle_digest(update, MagicMock())

    error_text = update.message.reply_text.call_args_list[1][0][0]
    assert "Error generating digest" in error_text
    assert "Ошибка при генерации" not in error_text


# ---------------------------------------------------------------------------
# handle_cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_cleanup_messages_use_output_language(english_config, mock_logger):
    """handle_cleanup processing and success messages respect output_language."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with patch("src.bot_commands.DigestSender") as mock_cls:
        mock_sender = MagicMock()
        mock_sender.cleanup_old_digests = AsyncMock(return_value=True)
        mock_cls.return_value = mock_sender
        await handler.handle_cleanup(update, MagicMock())

    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert any("Deleting previous digests" in t for t in texts)
    assert any("deleted" in t.lower() for t in texts)
    assert not any("Удаляю" in t for t in texts)
    assert not any("удалены" in t for t in texts)


# ---------------------------------------------------------------------------
# handle_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_status_uses_output_language(english_config, mock_logger):
    """handle_status status message respects output_language."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    await handler.handle_status(update, MagicMock())

    status_text = update.message.reply_text.call_args[0][0]
    assert "Telebrief Status" in status_text
    assert "Provider" in status_text
    assert "Model" in status_text
    assert "Enabled" in status_text or "Disabled" in status_text
    # No Russian
    assert "Статус Telebrief" not in status_text
    assert "Провайдер" not in status_text
    assert "Включена" not in status_text


# ---------------------------------------------------------------------------
# handle_help
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_help_uses_output_language(english_config, mock_logger):
    """handle_help text respects output_language."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    await handler.handle_help(update, MagicMock())

    help_text = update.message.reply_text.call_args[0][0]
    assert "Commands:" in help_text
    assert "Automatic mode:" in help_text
    assert "Features:" in help_text
    # No Russian structural labels
    assert "Команды:" not in help_text
    assert "Автоматический режим:" not in help_text
    assert "Возможности:" not in help_text


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_digest_rate_limited_on_rapid_successive_calls(english_config, mock_logger):
    """Rapid successive /digest commands from same user are throttled."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with patch(
        "src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=True)
    ):
        await handler.handle_digest(update, MagicMock())
        # Reset mock to track second call
        update.message.reply_text.reset_mock()
        await handler.handle_digest(update, MagicMock())

    # Second call should get rate limit message, not the "generating" message
    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert len(texts) == 1
    assert "wait" in texts[0].lower() or "Please wait" in texts[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_resets_after_cooldown(english_config, mock_logger):
    """Rate limit resets after the cooldown period elapses."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with (
        patch(
            "src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=True)
        ),
        patch("src.bot_commands.time") as mock_time,
    ):
        # First call at time 0
        mock_time.time.return_value = 0.0
        await handler.handle_digest(update, MagicMock())

        update.message.reply_text.reset_mock()

        # Second call at time 31 (past the 30s cooldown)
        mock_time.time.return_value = 31.0
        await handler.handle_digest(update, MagicMock())

    # Should get the normal "generating" message, not rate limited
    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert any("Generating" in t for t in texts)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rate_limit_message_uses_configured_language(sample_config, mock_logger):
    """Rate limit message is sent in the configured language (Russian)."""
    handler = BotCommandHandler(sample_config, mock_logger)
    update = _make_update(123456789)

    with patch(
        "src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=True)
    ):
        await handler.handle_digest(update, MagicMock())
        update.message.reply_text.reset_mock()
        await handler.handle_digest(update, MagicMock())

    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert len(texts) == 1
    assert "Пожалуйста" in texts[0] or "подождите" in texts[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_status_not_rate_limited(english_config, mock_logger):
    """/status is not rate limited — can be called rapidly."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    await handler.handle_status(update, MagicMock())
    update.message.reply_text.reset_mock()
    await handler.handle_status(update, MagicMock())

    # Second call should still get the status message, not a rate limit
    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert any("Telebrief Status" in t for t in texts)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_help_not_rate_limited(english_config, mock_logger):
    """/help is not rate limited — can be called rapidly."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    await handler.handle_help(update, MagicMock())
    update.message.reply_text.reset_mock()
    await handler.handle_help(update, MagicMock())

    # Second call should still get the help message
    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert any("Commands:" in t for t in texts)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_rate_limited(english_config, mock_logger):
    """Rapid successive /cleanup commands from same user are throttled."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with patch("src.bot_commands.DigestSender") as mock_cls:
        mock_sender = MagicMock()
        mock_sender.cleanup_old_digests = AsyncMock(return_value=True)
        mock_cls.return_value = mock_sender
        await handler.handle_cleanup(update, MagicMock())
        update.message.reply_text.reset_mock()
        await handler.handle_cleanup(update, MagicMock())

    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert len(texts) == 1
    assert "wait" in texts[0].lower() or "Please wait" in texts[0]
