"""Tests for formatter module."""

import pytest
from telegram import InlineKeyboardMarkup

from src.formatter import DigestFormatter


@pytest.mark.unit
def test_formatter_initialization(sample_config, mock_logger):
    """Test formatter initialization."""
    formatter = DigestFormatter(sample_config, mock_logger)

    assert formatter.config == sample_config
    assert formatter.logger == mock_logger
    assert formatter.use_emojis is True
    assert formatter.include_stats is True


@pytest.mark.unit
def test_create_digest(sample_config, mock_logger, sample_messages):
    """Test digest creation."""
    formatter = DigestFormatter(sample_config, mock_logger)

    overview = "Test overview summary"
    channel_summaries = {"Test Channel": "- Test point 1\n- Test point 2"}
    messages_by_channel = {"Test Channel": sample_messages}

    digest = formatter.create_digest(
        overview=overview,
        channel_summaries=channel_summaries,
        messages_by_channel=messages_by_channel,
        hours=24,
    )

    assert "Ежедневный дайджест" in digest
    assert overview in digest
    assert "Test point 1" in digest
    assert "Test Channel" in digest
    assert "Статистика" in digest


@pytest.mark.unit
def test_create_header(sample_config, mock_logger):
    """Test header creation."""
    formatter = DigestFormatter(sample_config, mock_logger)
    header = formatter._create_header(24)

    assert "Ежедневный дайджест" in header
    assert "📊" in header  # Emoji should be included


@pytest.mark.unit
def test_pick_emoji_tech(sample_config, mock_logger):
    """Test emoji selection for tech channels."""
    formatter = DigestFormatter(sample_config, mock_logger)

    assert formatter._pick_emoji("Tech News") == "💻"
    assert formatter._pick_emoji("Dev Channel") == "💻"
    assert formatter._pick_emoji("Программирование") == "💻"


@pytest.mark.unit
def test_pick_emoji_crypto(sample_config, mock_logger):
    """Test emoji selection for crypto channels."""
    formatter = DigestFormatter(sample_config, mock_logger)

    assert formatter._pick_emoji("Crypto News") == "💰"
    assert formatter._pick_emoji("Bitcoin Updates") == "💰"


@pytest.mark.unit
def test_pick_emoji_default(sample_config, mock_logger):
    """Test default emoji selection."""
    formatter = DigestFormatter(sample_config, mock_logger)

    assert formatter._pick_emoji("Random Channel") == "📺"


@pytest.mark.unit
def test_create_statistics(sample_config, mock_logger, sample_messages):
    """Test statistics creation."""
    formatter = DigestFormatter(sample_config, mock_logger)

    messages_by_channel = {
        "Channel 1": sample_messages,
        "Channel 2": sample_messages[:2],
    }

    stats = formatter._create_statistics(messages_by_channel, 24)

    assert "Статистика" in stats
    assert "2 каналов" in stats
    assert "5 сообщений" in stats
    assert "UTC" in stats


@pytest.mark.unit
def test_formatter_without_emojis(sample_config, mock_logger, sample_messages):
    """Test formatter with emojis disabled."""
    sample_config.settings.use_emojis = False
    formatter = DigestFormatter(sample_config, mock_logger)

    emoji = formatter._pick_emoji("Tech News")
    assert emoji == "•"  # Should return bullet instead of emoji


@pytest.mark.unit
def test_formatter_without_stats(sample_config, mock_logger, sample_messages):
    """Test formatter with statistics disabled."""
    sample_config.settings.include_statistics = False
    formatter = DigestFormatter(sample_config, mock_logger)

    overview = "Test overview"
    channel_summaries = {"Test Channel": "- Test point"}
    messages_by_channel = {"Test Channel": sample_messages}

    digest = formatter.create_digest(
        overview=overview,
        channel_summaries=channel_summaries,
        messages_by_channel=messages_by_channel,
        hours=24,
    )

    # Stats should not be included
    assert "Статистика" not in digest


@pytest.mark.unit
def test_build_toc_keyboard_private_chat(sample_config, mock_logger):
    """Test TOC keyboard uses tg://openmessage URLs for positive (private) chat_id."""
    formatter = DigestFormatter(sample_config, mock_logger)
    channel_id_map = [("Tech News", 101), ("Crypto News", 202)]
    chat_id = 123456

    keyboard = formatter.build_toc_keyboard(channel_id_map, chat_id)

    assert keyboard is not None
    assert isinstance(keyboard, InlineKeyboardMarkup)
    rows = keyboard.inline_keyboard
    assert len(rows) == 2
    btn0 = rows[0][0]
    btn1 = rows[1][0]
    assert btn0.url == "tg://openmessage?user_id=123456&message_id=101"
    assert btn1.url == "tg://openmessage?user_id=123456&message_id=202"


@pytest.mark.unit
def test_build_toc_keyboard_supergroup_chat(sample_config, mock_logger):
    """Test TOC keyboard uses https://t.me/c/ URLs for negative (supergroup) chat_id."""
    formatter = DigestFormatter(sample_config, mock_logger)
    channel_id_map = [("Tech News", 500)]
    chat_id = -1001234567890

    keyboard = formatter.build_toc_keyboard(channel_id_map, chat_id)

    assert keyboard is not None
    rows = keyboard.inline_keyboard
    assert len(rows) == 1
    btn = rows[0][0]
    assert btn.url == "https://t.me/c/1234567890/500"


@pytest.mark.unit
def test_build_toc_keyboard_button_labels(sample_config, mock_logger):
    """Test that button labels include the emoji and channel name."""
    formatter = DigestFormatter(sample_config, mock_logger)
    channel_id_map = [("Tech News", 1), ("Random Channel", 2)]
    chat_id = 99999

    keyboard = formatter.build_toc_keyboard(channel_id_map, chat_id)

    rows = keyboard.inline_keyboard
    assert "Tech News" in rows[0][0].text
    assert "💻" in rows[0][0].text  # tech emoji
    assert "Random Channel" in rows[1][0].text
    assert "📺" in rows[1][0].text  # default emoji


@pytest.mark.unit
def test_build_toc_keyboard_one_button_per_row(sample_config, mock_logger):
    """Test that each button is on its own row."""
    formatter = DigestFormatter(sample_config, mock_logger)
    channel_id_map = [("A", 1), ("B", 2), ("C", 3)]
    chat_id = 1

    keyboard = formatter.build_toc_keyboard(channel_id_map, chat_id)

    rows = keyboard.inline_keyboard
    assert len(rows) == 3
    for row in rows:
        assert len(row) == 1


@pytest.mark.unit
def test_build_toc_keyboard_empty_returns_none(sample_config, mock_logger):
    """Test that an empty channel_id_map returns None."""
    formatter = DigestFormatter(sample_config, mock_logger)

    result = formatter.build_toc_keyboard([], chat_id=123)

    assert result is None
