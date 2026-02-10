"""Tests for summarizer module."""

from unittest.mock import AsyncMock, patch

import pytest

from src.summarizer import SYSTEM_PROMPT_TEMPLATE, Summarizer


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarizer_initialization(sample_config, mock_logger):
    """Test summarizer initialization."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)

        assert summarizer.config == sample_config
        assert summarizer.logger == mock_logger
        assert summarizer.model == "gpt-5-nano"
        assert summarizer.temperature == 0.7
        assert summarizer.output_language == "Russian"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_all_empty(sample_config, mock_logger):
    """Test summarization with empty messages."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)

        messages_by_channel = {}
        result = await summarizer.summarize_all(messages_by_channel)

        assert result["channel_summaries"] == {}
        assert result["overview"] == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_all_success(sample_config, mock_logger, sample_messages):
    """Test successful summarization."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)

        messages_by_channel = {"Test Channel": sample_messages}

        # Mock the provider's chat_completion method
        summarizer.provider.chat_completion = AsyncMock(return_value="Test summary")

        result = await summarizer.summarize_all(messages_by_channel)

        assert "channel_summaries" in result
        assert "overview" in result
        assert "Test Channel" in result["channel_summaries"]
        assert result["channel_summaries"]["Test Channel"] == "Test summary"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_error(sample_config, mock_logger, sample_messages):
    """Test error handling in channel summarization."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)

        # Mock the provider to raise an exception
        summarizer.provider.chat_completion = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(Exception, match="API Error"):
            await summarizer._summarize_channel("Test Channel", sample_messages)


@pytest.mark.unit
def test_format_messages_for_prompt(sample_config, mock_logger, sample_messages):
    """Test message formatting for prompts."""
    with patch("src.ai_providers.AsyncOpenAI"):
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

    with patch("src.ai_providers.AsyncOpenAI"):
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
        assert len(formatted.split(": ", 1)[1]) <= 505  # 500 + some slack


@pytest.mark.unit
def test_system_prompt_template_language():
    """Test system prompt template accepts language parameter."""
    prompt = SYSTEM_PROMPT_TEMPLATE.format(language="English")
    assert "English" in prompt
    assert "{language}" not in prompt

    prompt_ru = SYSTEM_PROMPT_TEMPLATE.format(language="Russian")
    assert "Russian" in prompt_ru


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarizer_custom_output_language(sample_config, mock_logger, sample_messages):
    """Test summarizer uses configured output language in prompts."""
    sample_config.settings.output_language = "Spanish"

    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        assert summarizer.output_language == "Spanish"

        # Mock the provider's chat_completion to capture the messages
        captured_messages = []

        async def capture_chat(*args, **kwargs):
            captured_messages.append(kwargs.get("messages", args[0] if args else []))
            return "Test summary in Spanish"

        summarizer.provider.chat_completion = capture_chat

        result = await summarizer.summarize_all({"Test Channel": sample_messages})

        assert result["channel_summaries"]["Test Channel"] == "Test summary in Spanish"
        # Verify the system prompt contains "Spanish"
        assert len(captured_messages) == 1
        system_msg = captured_messages[0][0]["content"]
        user_msg = captured_messages[0][1]["content"]
        assert "Spanish" in system_msg
        assert "Spanish" in user_msg
