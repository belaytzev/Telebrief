"""Tests for bot_commands module — language / output_language coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot_commands import BotCommandHandler


def _make_callback_update(user_id: int, callback_data: str):
    """Return a minimal mock Update with a callback query."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.callback_query.data = callback_data
    update.callback_query.answer = AsyncMock()
    return update


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
async def test_handle_digest_processing_message_uses_output_language(
    english_config, mock_logger
):
    """handle_digest sends an English processing message when output_language=English."""
    handler = BotCommandHandler(english_config, mock_logger)
    update = _make_update(123456789)

    with patch("src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=True)):
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

    with patch("src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=True)):
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

    with patch("src.bot_commands.generate_and_send_channel_digests", new=AsyncMock(return_value=False)):
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
# handle_toc_callback
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_toc_callback_success(sample_config, mock_logger):
    """Authorized user triggers copy_message and query.answer is called."""
    handler = BotCommandHandler(sample_config, mock_logger)
    update = _make_callback_update(user_id=123456789, callback_data="toc:123456789:42")
    context = MagicMock()
    context.bot.copy_message = AsyncMock()

    await handler.handle_toc_callback(update, context)

    context.bot.copy_message.assert_called_once_with(
        chat_id=123456789,
        from_chat_id=123456789,
        message_id=42,
    )
    update.callback_query.answer.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_toc_callback_unauthorized(sample_config, mock_logger):
    """Unauthorized user does not trigger copy_message."""
    handler = BotCommandHandler(sample_config, mock_logger)
    update = _make_callback_update(user_id=999999, callback_data="toc:999999:42")
    context = MagicMock()
    context.bot.copy_message = AsyncMock()

    await handler.handle_toc_callback(update, context)

    context.bot.copy_message.assert_not_called()
    update.callback_query.answer.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_toc_callback_user_id_mismatch(sample_config, mock_logger):
    """Authorized caller with mismatched user_id in callback data does not trigger copy_message."""
    handler = BotCommandHandler(sample_config, mock_logger)
    # caller is the authorized user (123456789) but callback embeds a different user_id
    update = _make_callback_update(user_id=123456789, callback_data="toc:999999:42")
    context = MagicMock()
    context.bot.copy_message = AsyncMock()

    await handler.handle_toc_callback(update, context)

    context.bot.copy_message.assert_not_called()
    update.callback_query.answer.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_toc_callback_malformed_data(sample_config, mock_logger):
    """Malformed callback data does not trigger copy_message and still answers the query."""
    handler = BotCommandHandler(sample_config, mock_logger)
    update = _make_callback_update(user_id=123456789, callback_data="toc:notanint")
    context = MagicMock()
    context.bot.copy_message = AsyncMock()

    await handler.handle_toc_callback(update, context)

    context.bot.copy_message.assert_not_called()
    update.callback_query.answer.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_toc_callback_telegram_error(sample_config, mock_logger):
    """TelegramError from copy_message is caught; query.answer is still called with error text."""
    from telegram.error import TelegramError

    handler = BotCommandHandler(sample_config, mock_logger)
    update = _make_callback_update(user_id=123456789, callback_data="toc:123456789:42")
    context = MagicMock()
    context.bot.copy_message = AsyncMock(side_effect=TelegramError("message not found"))

    await handler.handle_toc_callback(update, context)

    update.callback_query.answer.assert_called_once()
    call_kwargs = update.callback_query.answer.call_args[1]
    assert "text" in call_kwargs
    assert "message not found" in call_kwargs["text"]
