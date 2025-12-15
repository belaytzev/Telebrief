"""Tests for formatter module."""

import pytest

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
