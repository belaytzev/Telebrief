"""Tests for summarizer module."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.summarizer import ERROR_SUMMARY_PREFIX, Summarizer, SYSTEM_PROMPT_TEMPLATE  # isort: skip
from src.ai_providers import TokenBudgetExhaustedError  # isort: skip


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
def _make_messages(count: int, text_len: int = 20):
    """Helper: build `count` messages with fixed-length text, ordered oldest-first."""
    from src.collector import Message

    return [
        Message(
            text="X" * text_len,
            sender="S",
            timestamp=datetime(2026, 1, 1, i, 0),
            link=f"https://t.me/test/{i}",
            channel_name="Test",
            has_media=False,
            media_type="",
        )
        for i in range(count)
    ]


@pytest.mark.unit
def test_format_messages_prompt_truncation_keeps_recent(sample_config, mock_logger):
    """When total chars exceed max_chars, only the most recent messages that fit are kept."""
    # Each formatted line: "N. [HH:MM] S: " (14 chars) + 20 X's = 34 chars
    # 2 messages + 1 newline = 34 + 1 + 34 = 69 chars → max_chars=70 keeps exactly 2
    messages = _make_messages(5, text_len=20)

    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        result = summarizer._format_messages_for_prompt(messages, max_chars=70)

    lines = result.split("\n")
    assert len(lines) == 2
    # Most recent timestamps should be present
    assert "04:00" in result
    assert "03:00" in result
    # Oldest timestamps must be absent
    assert "00:00" not in result
    assert "01:00" not in result


@pytest.mark.unit
def test_format_messages_prompt_no_truncation_within_budget(sample_config, mock_logger):
    """When total chars are within budget, all messages are included unchanged."""
    # 5 messages × 34 chars + 4 newlines = 174 chars → max_chars=200 fits all
    messages = _make_messages(5, text_len=20)

    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        result = summarizer._format_messages_for_prompt(messages, max_chars=200)

    lines = result.split("\n")
    assert len(lines) == 5
    assert "00:00" in result
    assert "04:00" in result


@pytest.mark.unit
def test_format_messages_prompt_always_includes_at_least_one(sample_config, mock_logger):
    """Even with max_chars=1, the single most recent message is always included."""
    messages = _make_messages(5, text_len=20)

    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        result = summarizer._format_messages_for_prompt(messages, max_chars=1)

    lines = [line for line in result.split("\n") if line]
    assert len(lines) == 1
    assert "04:00" in result  # most recent


@pytest.mark.unit
def test_format_messages_prompt_warns_on_truncation(sample_config, mock_logger):
    """A WARNING is logged when messages are dropped due to the budget."""
    messages = _make_messages(5, text_len=20)

    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer._format_messages_for_prompt(messages, max_chars=70)

    mock_logger.warning.assert_called()
    warning_text = str(mock_logger.warning.call_args)
    assert "truncat" in warning_text.lower() or "kept" in warning_text.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_passes_max_prompt_chars_to_formatter(
    sample_config, mock_logger, sample_messages
):
    """_summarize_channel passes config.settings.max_prompt_chars to _format_messages_for_prompt."""
    sample_config.settings.max_prompt_chars = 1234

    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(return_value="summary")

        captured_max_chars = []
        original_format = summarizer._format_messages_for_prompt

        def patched_format(messages, max_chars=8000):
            captured_max_chars.append(max_chars)
            return original_format(messages, max_chars)

        summarizer._format_messages_for_prompt = patched_format
        await summarizer._summarize_channel("Test", sample_messages)

    assert captured_max_chars == [1234]


@pytest.mark.unit
def test_system_prompt_template_language():
    """Test system prompt template accepts language parameter."""
    prompt = SYSTEM_PROMPT_TEMPLATE.replace("{language}", "English")
    assert "English" in prompt
    assert "{language}" not in prompt

    prompt_ru = SYSTEM_PROMPT_TEMPLATE.replace("{language}", "Russian")
    assert "Russian" in prompt_ru


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_all_partial_failure(sample_config, mock_logger, sample_messages):
    """Test that summarize_all catches per-channel errors and continues."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)

        summarizer.provider.chat_completion = AsyncMock(side_effect=Exception("API timeout"))

        result = await summarizer.summarize_all({"Failing Channel": sample_messages})

        assert "Failing Channel" in result["channel_summaries"]
        assert ERROR_SUMMARY_PREFIX in result["channel_summaries"]["Failing Channel"]


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_retries_on_token_budget_exhausted(
    sample_config, mock_logger, sample_messages
):
    """_summarize_channel retries with max_tokens*3 when TokenBudgetExhaustedError is raised."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(
            side_effect=[TokenBudgetExhaustedError("budget exhausted"), "Retry summary"]
        )
        result = await summarizer._summarize_channel("Test Channel", sample_messages)

        assert result == "Retry summary"
        assert summarizer.provider.chat_completion.call_count == 2
        first_max = summarizer.provider.chat_completion.call_args_list[0].kwargs["max_tokens"]
        second_max = summarizer.provider.chat_completion.call_args_list[1].kwargs["max_tokens"]
        assert second_max == first_max * 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_retry_failure_propagates(
    sample_config, mock_logger, sample_messages
):
    """_summarize_channel lets the retry exception propagate when the second call also fails."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(
            side_effect=[
                TokenBudgetExhaustedError("budget exhausted"),
                RuntimeError("network error"),
            ]
        )
        with pytest.raises(RuntimeError, match="network error"):
            await summarizer._summarize_channel("Test Channel", sample_messages)

        assert summarizer.provider.chat_completion.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_no_retry_on_success(sample_config, mock_logger, sample_messages):
    """_summarize_channel calls chat_completion exactly once when the first call succeeds."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(return_value="Success summary")

        result = await summarizer._summarize_channel("Test Channel", sample_messages)

        assert result == "Success summary"
        assert summarizer.provider.chat_completion.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_double_budget_exhaustion_propagates(
    sample_config, mock_logger, sample_messages
):
    """If the retry also raises TokenBudgetExhaustedError it propagates without further retry."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(
            side_effect=[
                TokenBudgetExhaustedError("first exhaustion"),
                TokenBudgetExhaustedError("second exhaustion"),
            ]
        )
        with pytest.raises(TokenBudgetExhaustedError, match="second exhaustion"):
            await summarizer._summarize_channel("Test Channel", sample_messages)

        assert summarizer.provider.chat_completion.call_count == 2
