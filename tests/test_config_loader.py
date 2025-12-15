"""Tests for config_loader module."""

from unittest.mock import patch

import pytest

from src.config_loader import load_config


@pytest.mark.unit
def test_load_config_success(temp_config_file, mock_env_vars):
    """Test successful configuration loading."""
    config = load_config(temp_config_file)

    assert config is not None
    assert len(config.channels) == 2
    assert config.channels[0].id == "@test_channel"
    assert config.channels[0].name == "Test Channel"
    assert config.settings.schedule_time == "08:00"
    assert config.settings.target_user_id == 123456789
    assert config.telegram_api_id == 12345678
    assert config.openai_api_key == "sk-test-key"


@pytest.mark.unit
def test_load_config_missing_file():
    """Test error handling for missing config file."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")


@pytest.mark.unit
def test_load_config_missing_env_vars(tmp_path, monkeypatch):
    """Test error handling for missing environment variables."""
    # Create temp config file without using mock_env_vars
    config_content = """
channels:
  - id: "@test_channel"
    name: "Test Channel"

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    # Remove all required env vars
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Mock load_dotenv to prevent loading from .env file
    with patch("src.config_loader.load_dotenv"):
        with pytest.raises(ValueError, match="Missing required environment variables"):
            load_config(str(config_file))


@pytest.mark.unit
def test_load_config_invalid_target_user(tmp_path, mock_env_vars):
    """Test error handling for invalid target user ID."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 0
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="target_user_id not configured"):
        load_config(str(config_file))


@pytest.mark.unit
def test_load_config_no_channels(tmp_path, mock_env_vars):
    """Test error handling for no channels configured."""
    config_content = """
channels: []

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="No channels configured"):
        load_config(str(config_file))
