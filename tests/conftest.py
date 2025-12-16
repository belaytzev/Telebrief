"""Pytest configuration and fixtures."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.config_loader import ChannelConfig, Config, Settings


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("TELEGRAM_API_ID", "12345678")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    channels = [
        ChannelConfig(id="@test_channel", name="Test Channel"),
        ChannelConfig(id="-1001234567890", name="Private Group"),
    ]

    settings = Settings(
        schedule_time="08:00",
        timezone="UTC",
        lookback_hours=24,
        openai_model="gpt-5-nano",
        openai_temperature=0.7,
        max_tokens_per_summary=500,
        use_emojis=True,
        include_statistics=True,
        target_user_id=123456789,
        auto_cleanup_old_digests=True,
        max_messages_per_channel=500,
        api_timeout=30,
    )

    config = Config(
        channels=channels,
        settings=settings,
        telegram_api_id=12345678,
        telegram_api_hash="test_hash",
        telegram_bot_token="123456789:ABC-DEF",
        openai_api_key="sk-test-key",
        log_level="INFO",
    )

    return config


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    from src.collector import Message

    return [
        Message(
            text="Test message 1",
            sender="User1",
            timestamp=datetime(2025, 12, 14, 10, 0, 0),
            link="https://t.me/test/1",
            channel_name="Test Channel",
            has_media=False,
            media_type="",
        ),
        Message(
            text="Test message 2",
            sender="User2",
            timestamp=datetime(2025, 12, 14, 11, 0, 0),
            link="https://t.me/test/2",
            channel_name="Test Channel",
            has_media=True,
            media_type="Фото",
        ),
        Message(
            text="Test message 3",
            sender="User3",
            timestamp=datetime(2025, 12, 14, 12, 0, 0),
            link="https://t.me/test/3",
            channel_name="Test Channel",
            has_media=False,
            media_type="",
        ),
    ]


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def temp_config_file(tmp_path, mock_env_vars):
    """Create a temporary config file."""
    config_content = """
channels:
  - id: "@test_channel"
    name: "Test Channel"
  - id: -1001234567890
    name: "Private Group"

settings:
  schedule_time: "08:00"
  timezone: "UTC"
  lookback_hours: 24
  openai_model: "gpt-5-nano"
  openai_temperature: 0.7
  max_tokens_per_summary: 500
  use_emojis: true
  include_statistics: true
  target_user_id: 123456789
  auto_cleanup_old_digests: true
  max_messages_per_channel: 500
  api_timeout: 30
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)
