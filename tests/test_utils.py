"""Tests for utils module."""

from datetime import datetime, timedelta

import pytest

from src.utils import get_lookback_time, split_message


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
