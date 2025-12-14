"""Tests for utils module."""

from datetime import datetime, timedelta

import pytest

from src.utils import (
    estimate_tokens,
    format_cost,
    format_timerange,
    get_lookback_time,
    split_message,
    truncate_text,
)


@pytest.mark.unit
def test_format_timerange():
    """Test time range formatting."""
    assert format_timerange(1) == "последний 1ч"
    assert format_timerange(2) == "последние 2ч"
    assert format_timerange(24) == "последние 24ч"


@pytest.mark.unit
def test_get_lookback_time():
    """Test lookback time calculation."""
    now = datetime.utcnow()
    lookback = get_lookback_time(24)

    assert isinstance(lookback, datetime)
    assert lookback < now
    # Should be approximately 24 hours ago (within 1 minute)
    expected = now - timedelta(hours=24)
    assert abs((lookback - expected).total_seconds()) < 60


@pytest.mark.unit
def test_truncate_text_short():
    """Test truncation with short text."""
    text = "Short text"
    result = truncate_text(text, max_length=100)
    assert result == text


@pytest.mark.unit
def test_truncate_text_long():
    """Test truncation with long text."""
    text = "A" * 5000
    result = truncate_text(text, max_length=4000)

    assert len(result) <= 4000
    assert "обрезано" in result


@pytest.mark.unit
def test_split_message_short():
    """Test message splitting with short text."""
    text = "Short message"
    parts = split_message(text, max_length=4000)

    assert len(parts) == 1
    assert parts[0] == text


@pytest.mark.unit
def test_split_message_long():
    """Test message splitting with long text."""
    lines = ["Line " + str(i) for i in range(1000)]
    text = "\n".join(lines)

    parts = split_message(text, max_length=1000)

    assert len(parts) > 1
    # All parts should be within limit
    for part in parts:
        assert len(part) <= 1000
    # Reassembling should give similar line count
    total_lines = sum(part.count("\n") for part in parts)
    assert total_lines >= 900  # Some lines might be split


@pytest.mark.unit
def test_estimate_tokens():
    """Test token estimation."""
    text = "This is a test message"  # ~22 chars
    tokens = estimate_tokens(text)

    assert tokens > 0
    assert tokens == len(text) // 4  # Rough estimate


@pytest.mark.unit
def test_format_cost_gpt4():
    """Test cost formatting for GPT-4."""
    cost = format_cost(1000, 500, "gpt-4-turbo-preview")

    assert cost.startswith("$")
    assert float(cost[1:]) > 0


@pytest.mark.unit
def test_format_cost_gpt35():
    """Test cost formatting for GPT-3.5."""
    cost = format_cost(1000, 500, "gpt-3.5-turbo")

    assert cost.startswith("$")
    gpt4_cost = float(format_cost(1000, 500, "gpt-4-turbo-preview")[1:])
    gpt35_cost = float(cost[1:])
    assert gpt35_cost < gpt4_cost  # GPT-3.5 should be cheaper
