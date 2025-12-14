"""Tests for summarizer module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.summarizer import Summarizer


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarizer_initialization(sample_config, mock_logger):
    """Test summarizer initialization."""
    summarizer = Summarizer(sample_config, mock_logger)

    assert summarizer.config == sample_config
    assert summarizer.logger == mock_logger
    assert summarizer.model == "gpt-4-turbo-preview"
    assert summarizer.temperature == 0.7


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_all_empty(sample_config, mock_logger):
    """Test summarization with empty messages."""
    summarizer = Summarizer(sample_config, mock_logger)

    messages_by_channel = {}
    result = await summarizer.summarize_all(messages_by_channel)

    assert result["channel_summaries"] == {}
    assert "Нет сообщений" in result["overview"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_all_success(sample_config, mock_logger, sample_messages):
    """Test successful summarization."""
    summarizer = Summarizer(sample_config, mock_logger)

    messages_by_channel = {"Test Channel": sample_messages}

    # Mock OpenAI API
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test summary"))]

    with patch.object(
        summarizer.client.chat.completions, "create", new=AsyncMock(return_value=mock_response)
    ):
        result = await summarizer.summarize_all(messages_by_channel)

    assert "channel_summaries" in result
    assert "overview" in result
    assert "Test Channel" in result["channel_summaries"]
    assert result["channel_summaries"]["Test Channel"] == "Test summary"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_error(sample_config, mock_logger, sample_messages):
    """Test error handling in channel summarization."""
    summarizer = Summarizer(sample_config, mock_logger)

    # Mock OpenAI API to raise exception
    with patch.object(
        summarizer.client.chat.completions,
        "create",
        new=AsyncMock(side_effect=Exception("API Error")),
    ):
        with pytest.raises(Exception, match="API Error"):
            await summarizer._summarize_channel("Test Channel", sample_messages)


@pytest.mark.unit
def test_format_messages_for_prompt(sample_config, mock_logger, sample_messages):
    """Test message formatting for prompts."""
    summarizer = Summarizer(sample_config, mock_logger)

    formatted = summarizer._format_messages_for_prompt(sample_messages)

    assert "User1" in formatted
    assert "Test message 1" in formatted
    assert "10:00" in formatted


@pytest.mark.unit
def test_format_messages_truncate_long(sample_config, mock_logger):
    """Test message truncation in formatting."""
    from datetime import datetime

    from src.collector import Message

    summarizer = Summarizer(sample_config, mock_logger)

    long_message = Message(
        text="A" * 600,  # Longer than 500 char limit
        sender="User",
        timestamp=datetime(2025, 12, 14, 10, 0, 0),
        link="https://t.me/test/1",
        channel_name="Test",
        has_media=False,
        media_type="",
    )

    formatted = summarizer._format_messages_for_prompt([long_message])

    # Should be truncated to 500 chars
    assert len(formatted.split(": ", 1)[1]) <= 505  # 500 + some slack for formatting
