"""Tests for formatter module."""

import pytest

from src.formatter import DigestFormatter


@pytest.fixture
def english_config(sample_config):
    """sample_config with output_language set to English."""
    sample_config.settings.output_language = "English"
    return sample_config


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


# --- Language / output_language tests ---


@pytest.mark.unit
def test_create_header_uses_output_language(english_config, mock_logger):
    """Header uses output_language: English config produces English header."""
    formatter = DigestFormatter(english_config, mock_logger)
    header = formatter._create_header(24)

    assert "Daily Digest" in header
    assert "Ежедневный дайджест" not in header


@pytest.mark.unit
def test_format_summary_message_uses_output_language(english_config, mock_logger):
    """format_summary_message respects output_language."""
    formatter = DigestFormatter(english_config, mock_logger)
    msg = formatter.format_summary_message(total_channels=3, total_messages=42, hours=24)

    assert "Digest completed" in msg
    assert "Channels processed" in msg
    assert "Total messages" in msg
    assert "Period" in msg
    assert "Дайджест завершён" not in msg
    assert "Обработано каналов" not in msg


@pytest.mark.unit
def test_create_statistics_uses_output_language(english_config, mock_logger, sample_messages):
    """_create_statistics respects output_language."""
    formatter = DigestFormatter(english_config, mock_logger)
    messages_by_channel = {"Ch1": sample_messages, "Ch2": sample_messages[:1]}

    stats = formatter._create_statistics(messages_by_channel, 24)

    assert "Statistics" in stats
    assert "channels" in stats
    assert "messages processed" in stats
    assert "Статистика" not in stats
    assert "каналов" not in stats


@pytest.mark.unit
def test_format_channel_message_stats_uses_output_language(
    english_config, mock_logger, sample_messages
):
    """format_channel_message per-channel stats respect output_language."""
    formatter = DigestFormatter(english_config, mock_logger)
    msg = formatter.format_channel_message("MyChannel", "Summary text", sample_messages, hours=24)

    assert "Messages processed" in msg
    assert "Обработано сообщений" not in msg


@pytest.mark.unit
def test_overview_section_label_uses_output_language(english_config, mock_logger, sample_messages):
    """create_digest overview section label respects output_language."""
    formatter = DigestFormatter(english_config, mock_logger)
    digest = formatter.create_digest(
        overview="Some overview",
        channel_summaries={"Ch": "- point"},
        messages_by_channel={"Ch": sample_messages},
        hours=24,
    )

    assert "Brief Overview" in digest
    assert "Краткий обзор" not in digest


@pytest.mark.unit
def test_truncation_message_uses_output_language(english_config, mock_logger, sample_messages):
    """Truncation suffix in format_channel_message respects output_language."""
    formatter = DigestFormatter(english_config, mock_logger)
    # Long summary ensures total message exceeds 4096 chars and triggers truncation
    long_summary = "word " * 1000
    msg = formatter.format_channel_message("Ch", long_summary, sample_messages, hours=24)

    assert "truncated due to length limit" in msg
    assert "усечено" not in msg


@pytest.mark.unit
def test_format_date_russian_month_names(sample_config, mock_logger):
    """_format_date returns Russian month names when output_language is Russian."""
    from datetime import datetime

    formatter = DigestFormatter(sample_config, mock_logger)  # output_language=Russian
    # February in Russian genitive (used in dates) is "февраля"
    dt = datetime(2026, 2, 22)
    result = formatter._format_date(dt)

    assert "февраля" in result
    assert "February" not in result


@pytest.mark.unit
def test_format_date_english_month_names(english_config, mock_logger):
    """_format_date returns English month names when output_language is English."""
    from datetime import datetime

    formatter = DigestFormatter(english_config, mock_logger)
    dt = datetime(2026, 2, 22)
    result = formatter._format_date(dt)

    assert "February" in result
    assert "Февраль" not in result


@pytest.mark.unit
def test_create_header_russian_month_name(sample_config, mock_logger):
    """_create_header uses localized month name for Russian output_language."""
    formatter = DigestFormatter(sample_config, mock_logger)
    header = formatter._create_header(24)

    # Month names in Russian must not contain English month strings (spot-check Jan-Mar)
    assert "January" not in header
    assert "February" not in header
    assert "March" not in header
