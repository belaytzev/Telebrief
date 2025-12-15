"""Tests for utils module."""

import json
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.utils import (
    clear_digest_message_ids,
    get_digest_message_ids,
    get_lookback_time,
    save_digest_message_ids,
    setup_logging,
    split_message,
)


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


@pytest.mark.unit
def test_split_message_very_long_line():
    """Test message splitting with a very long line."""
    # Create a line longer than max_length
    long_line = "A" * 5000
    text = f"Start\n{long_line}\nEnd"

    parts = split_message(text, max_length=1000)

    assert len(parts) > 1
    # All parts should be within limit
    for part in parts:
        assert len(part) <= 1000


@pytest.mark.unit
def test_split_message_exact_boundary():
    """Test message splitting at exact boundary."""
    text = "A" * 1000
    parts = split_message(text, max_length=1000)

    assert len(parts) == 1
    assert parts[0] == text


@pytest.mark.unit
def test_setup_logging_info_level(tmp_path):
    """Test setup_logging with INFO level."""
    import os

    # Change to temp directory
    original_dir = os.getcwd()
    os.chdir(tmp_path)

    try:
        logger = setup_logging("INFO")

        assert logger.name == "telebrief"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 2  # Console and file handlers

        # Check log file was created
        log_file = tmp_path / "logs" / "telebrief.log"
        assert log_file.exists()

    finally:
        # Restore original directory
        os.chdir(original_dir)


@pytest.mark.unit
def test_setup_logging_debug_level(tmp_path):
    """Test setup_logging with DEBUG level."""
    import os

    original_dir = os.getcwd()
    os.chdir(tmp_path)

    try:
        logger = setup_logging("DEBUG")

        assert logger.level == logging.DEBUG

        # Test that logger can log
        logger.debug("Test debug message")
        logger.info("Test info message")

    finally:
        os.chdir(original_dir)


@pytest.mark.unit
def test_save_and_get_digest_message_ids(tmp_path, monkeypatch):
    """Test saving and retrieving message IDs."""
    # Use temp directory for storage
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    user_id = 123456
    message_ids = [1, 2, 3, 4, 5]

    # Save message IDs
    save_digest_message_ids(message_ids, user_id)

    # Verify file was created
    assert storage_file.exists()

    # Retrieve message IDs
    retrieved_ids = get_digest_message_ids(user_id)
    assert retrieved_ids == message_ids


@pytest.mark.unit
def test_get_digest_message_ids_no_file(tmp_path, monkeypatch):
    """Test getting message IDs when file doesn't exist."""
    storage_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    user_id = 123456
    retrieved_ids = get_digest_message_ids(user_id)

    assert retrieved_ids == []


@pytest.mark.unit
def test_get_digest_message_ids_invalid_json(tmp_path, monkeypatch):
    """Test getting message IDs with corrupted JSON file."""
    storage_file = tmp_path / "corrupt.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    # Create corrupted JSON file
    storage_file.write_text("invalid json {{{")

    user_id = 123456
    retrieved_ids = get_digest_message_ids(user_id)

    assert retrieved_ids == []


@pytest.mark.unit
def test_clear_digest_message_ids(tmp_path, monkeypatch):
    """Test clearing message IDs."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    user_id = 123456
    message_ids = [1, 2, 3]

    # Save message IDs
    save_digest_message_ids(message_ids, user_id)

    # Clear them
    clear_digest_message_ids(user_id)

    # Verify they're cleared
    retrieved_ids = get_digest_message_ids(user_id)
    assert retrieved_ids == []


@pytest.mark.unit
def test_clear_digest_message_ids_no_file(tmp_path, monkeypatch):
    """Test clearing message IDs when file doesn't exist."""
    storage_file = tmp_path / "nonexistent.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    user_id = 123456

    # Should not raise error
    clear_digest_message_ids(user_id)


@pytest.mark.unit
def test_save_digest_message_ids_multiple_users(tmp_path, monkeypatch):
    """Test saving message IDs for multiple users."""
    storage_file = tmp_path / "digest_messages.json"
    monkeypatch.setattr("src.utils.MESSAGE_STORAGE_FILE", str(storage_file))

    user1_id = 111
    user2_id = 222
    user1_messages = [1, 2, 3]
    user2_messages = [4, 5, 6]

    # Save for both users
    save_digest_message_ids(user1_messages, user1_id)
    save_digest_message_ids(user2_messages, user2_id)

    # Retrieve and verify
    assert get_digest_message_ids(user1_id) == user1_messages
    assert get_digest_message_ids(user2_id) == user2_messages
