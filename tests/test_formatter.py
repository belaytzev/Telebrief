"""Tests for formatter module."""

import pytest

from src.formatter import DigestFormatter
from src.grouper import GroupedPoint


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
    assert "5 сообщений обработано" in stats
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


# --- Channel URL extraction tests ---


@pytest.mark.unit
def test_extract_channel_url_public(sample_config, mock_logger):
    """Extracts base channel URL from a public message link."""
    from datetime import datetime

    from src.collector import Message

    messages = [
        Message(
            text="hi",
            sender="u",
            timestamp=datetime(2026, 1, 1),
            link="https://t.me/mychannel/42",
            channel_name="Test",
            has_media=False,
            media_type="",
        )
    ]
    formatter = DigestFormatter(sample_config, mock_logger)
    assert formatter._extract_channel_url(messages) == "https://t.me/mychannel"


@pytest.mark.unit
def test_extract_channel_url_private(sample_config, mock_logger):
    """Extracts base channel URL from a private message link."""
    from datetime import datetime

    from src.collector import Message

    messages = [
        Message(
            text="hi",
            sender="u",
            timestamp=datetime(2026, 1, 1),
            link="https://t.me/c/1234567890/42",
            channel_name="Test",
            has_media=False,
            media_type="",
        )
    ]
    formatter = DigestFormatter(sample_config, mock_logger)
    assert formatter._extract_channel_url(messages) == "https://t.me/c/1234567890"


@pytest.mark.unit
def test_extract_channel_url_no_messages(sample_config, mock_logger):
    """Returns None when no messages are provided."""
    formatter = DigestFormatter(sample_config, mock_logger)
    assert formatter._extract_channel_url([]) is None


@pytest.mark.unit
def test_extract_channel_url_fallback_link(sample_config, mock_logger):
    """Returns None when all message links are '#' fallback."""
    from datetime import datetime

    from src.collector import Message

    messages = [
        Message(
            text="hi",
            sender="u",
            timestamp=datetime(2026, 1, 1),
            link="#",
            channel_name="Test",
            has_media=False,
            media_type="",
        )
    ]
    formatter = DigestFormatter(sample_config, mock_logger)
    assert formatter._extract_channel_url(messages) is None


@pytest.mark.unit
def test_channel_section_includes_channel_link(sample_config, mock_logger, sample_messages):
    """Channel section header includes a clickable link to the channel."""
    formatter = DigestFormatter(sample_config, mock_logger)
    section = formatter._create_channel_section("Test Channel", "Summary", sample_messages)
    # sample_messages links are https://t.me/test/1 etc → channel URL is https://t.me/test
    assert "https://t.me/test" in section


@pytest.mark.unit
def test_format_channel_message_includes_channel_link(sample_config, mock_logger, sample_messages):
    """format_channel_message header includes a clickable link to the channel."""
    formatter = DigestFormatter(sample_config, mock_logger)
    msg = formatter.format_channel_message("Test Channel", "Summary", sample_messages)
    assert "https://t.me/test" in msg


@pytest.mark.unit
def test_channel_section_no_link_when_no_messages(sample_config, mock_logger):
    """Channel section omits channel link gracefully when no messages provided."""
    formatter = DigestFormatter(sample_config, mock_logger)
    section = formatter._create_channel_section("Test Channel", "Summary", [])
    assert "https://t.me" not in section


# --- Group formatter tests ---


@pytest.mark.unit
def test_pick_group_emoji_known_groups(sample_config, mock_logger):
    """_pick_group_emoji returns correct emoji for known group names."""
    formatter = DigestFormatter(sample_config, mock_logger)

    assert formatter._pick_group_emoji("Events") == "🎪"
    assert formatter._pick_group_emoji("event") == "🎪"
    assert formatter._pick_group_emoji("News") == "📰"
    assert formatter._pick_group_emoji("news") == "📰"
    assert formatter._pick_group_emoji("Sport") == "⚽"
    assert formatter._pick_group_emoji("sports") == "⚽"
    assert formatter._pick_group_emoji("Other") == "📌"
    assert formatter._pick_group_emoji("other") == "📌"


@pytest.mark.unit
def test_pick_group_emoji_default(sample_config, mock_logger):
    """_pick_group_emoji returns default emoji for unknown groups."""
    formatter = DigestFormatter(sample_config, mock_logger)
    assert formatter._pick_group_emoji("RandomTopic") == "📌"


@pytest.mark.unit
def test_format_group_message_output(english_config, mock_logger):
    """format_group_message produces expected format with source attribution."""
    formatter = DigestFormatter(english_config, mock_logger)
    points = [
        GroupedPoint(point="Python 3.14 released", source="TechNews"),
        GroupedPoint(point="New AI model announced", source="AIDaily"),
    ]
    msg = formatter.format_group_message("News", points, hours=24)

    assert "📰 News" in msg
    assert "Python 3.14 released" in msg
    assert "from TechNews" in msg
    assert "New AI model announced" in msg
    assert "from AIDaily" in msg
    assert "2 items" in msg


@pytest.mark.unit
def test_format_group_message_truncation(english_config, mock_logger):
    """format_group_message truncates at 4096 chars."""
    formatter = DigestFormatter(english_config, mock_logger)
    # Create enough points to exceed 4096 chars
    points = [GroupedPoint(point="x" * 200, source="Ch") for _ in range(30)]
    msg = formatter.format_group_message("News", points, hours=24)

    assert len(msg) <= 4096  # must fit within Telegram's message limit
    assert "truncated" in msg


@pytest.mark.unit
def test_format_group_message_empty_points(english_config, mock_logger):
    """format_group_message returns empty string for empty points list."""
    formatter = DigestFormatter(english_config, mock_logger)
    msg = formatter.format_group_message("News", [], hours=24)
    assert msg == ""


@pytest.mark.unit
def test_format_group_message_no_source(english_config, mock_logger):
    """format_group_message omits source tag when source is empty."""
    formatter = DigestFormatter(english_config, mock_logger)
    points = [GroupedPoint(point="Some point", source="")]
    msg = formatter.format_group_message("News", points, hours=24)

    assert "Some point" in msg
    assert "from" not in msg


@pytest.mark.unit
def test_format_group_summary_message(english_config, mock_logger):
    """format_group_summary_message produces expected header format."""
    formatter = DigestFormatter(english_config, mock_logger)
    msg = formatter.format_group_summary_message(
        group_names=["Events", "News", "Other"],
        total_points=42,
        hours=24,
    )

    assert "Digest completed" in msg
    assert "🎪 Events" in msg
    assert "📰 News" in msg
    assert "📌 Other" in msg
    assert "42 items" in msg
    assert "UTC" in msg


@pytest.mark.unit
def test_format_group_summary_message_russian(sample_config, mock_logger):
    """format_group_summary_message respects output_language (Russian)."""
    formatter = DigestFormatter(sample_config, mock_logger)
    msg = formatter.format_group_summary_message(
        group_names=["Events"],
        total_points=10,
        hours=24,
    )

    assert "Дайджест завершён" in msg
    assert "Группы" in msg
