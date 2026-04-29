"""Tests for config_loader module."""

import logging
from unittest.mock import patch

import pytest

from src.config_loader import DigestGroupConfig, StorageConfig, load_config


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
    assert config.settings.ai_provider == "openai"
    assert config.settings.ai_model == "gpt-5-nano"
    assert config.settings.output_language == "Russian"


@pytest.mark.unit
def test_load_config_custom_output_language(tmp_path, mock_env_vars):
    """Test config loading with custom output_language."""
    config_content = """
channels:
  - id: "@test_channel"
    name: "Test Channel"

settings:
  target_user_id: 123456789
  output_language: "English"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.output_language == "English"


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


@pytest.mark.unit
def test_load_config_ollama_provider(tmp_path, monkeypatch):
    """Test config loading with Ollama provider (no API keys needed)."""
    monkeypatch.setenv("TELEGRAM_API_ID", "12345678")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")

    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  ai_provider: "ollama"
  ai_model: "llama3"
  ollama_base_url: "http://myserver:11434"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with patch("src.config_loader.load_dotenv"):
        config = load_config(str(config_file))

    assert config.settings.ai_provider == "ollama"
    assert config.settings.ai_model == "llama3"
    assert config.settings.ollama_base_url == "http://myserver:11434"


@pytest.mark.unit
def test_load_config_anthropic_provider_missing_key(tmp_path, monkeypatch):
    """Test Anthropic provider requires ANTHROPIC_API_KEY."""
    monkeypatch.setenv("TELEGRAM_API_ID", "12345678")
    monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  ai_provider: "anthropic"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with patch("src.config_loader.load_dotenv"):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            load_config(str(config_file))


@pytest.mark.unit
def test_load_config_unsupported_provider(tmp_path, mock_env_vars):
    """Test error for unsupported ai_provider value."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  ai_provider: "gemini"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Unsupported ai_provider"):
        load_config(str(config_file))


@pytest.mark.unit
def test_load_config_null_ai_provider(tmp_path, mock_env_vars):
    """Test that ai_provider: null gives a clear ValueError, not AttributeError."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  ai_provider: null
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="ai_provider must be a string"):
        load_config(str(config_file))


@pytest.mark.unit
def test_load_config_temperature_fallback(tmp_path, mock_env_vars):
    """Test that temperature falls back to openai_temperature when not set."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  openai_temperature: 0.5
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.temperature == 0.5
    assert config.settings.openai_temperature == 0.5


@pytest.mark.unit
def test_load_config_temperature_override(tmp_path, mock_env_vars):
    """Test that explicit temperature overrides openai_temperature."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  openai_temperature: 0.5
  temperature: 0.9
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.temperature == 0.9


@pytest.mark.unit
def test_load_config_api_timeout_string_coercion(tmp_path, mock_env_vars):
    """Test that api_timeout is coerced to int even when YAML provides a string."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  api_timeout: "60"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.api_timeout == 60
    assert isinstance(config.settings.api_timeout, int)


@pytest.mark.unit
def test_load_config_default_max_tokens_per_summary(tmp_path, mock_env_vars):
    """Test that max_tokens_per_summary defaults to 1500 when not specified."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.max_tokens_per_summary == 1500


@pytest.mark.unit
def test_load_config_default_max_prompt_chars(tmp_path, mock_env_vars):
    """Test that max_prompt_chars defaults to 8000 when not specified."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.max_prompt_chars == 8000


@pytest.mark.unit
def test_load_config_custom_max_prompt_chars(tmp_path, mock_env_vars):
    """Test that max_prompt_chars is loaded correctly from YAML."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  max_prompt_chars: 4000
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.max_prompt_chars == 4000


@pytest.mark.unit
def test_load_config_digest_mode_with_groups(tmp_path, mock_env_vars):
    """Test valid digest config loads correctly."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  digest_mode: "digest"
  digest_groups:
    - name: "Events"
      description: "Conferences and meetups"
    - name: "News"
      description: "World affairs"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.digest_mode == "digest"
    assert len(config.settings.digest_groups) == 2
    assert config.settings.digest_groups[0] == DigestGroupConfig(
        name="Events", description="Conferences and meetups"
    )
    assert config.settings.digest_groups[1] == DigestGroupConfig(
        name="News", description="World affairs"
    )


@pytest.mark.unit
def test_load_config_digest_defaults(tmp_path, mock_env_vars):
    """Test missing digest_groups defaults to empty list, digest_mode defaults to channel."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    assert config.settings.digest_mode == "channel"
    assert config.settings.digest_groups == []


@pytest.mark.unit
def test_load_config_invalid_digest_mode(tmp_path, mock_env_vars):
    """Test invalid digest_mode value raises ValueError."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  digest_mode: "invalid"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Invalid digest_mode"):
        load_config(str(config_file))


@pytest.mark.unit
def test_load_config_digest_mode_empty_groups_warns(tmp_path, mock_env_vars, caplog):
    """Test digest_mode 'digest' with empty digest_groups logs warning."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  digest_mode: "digest"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with caplog.at_level(logging.WARNING, logger="telebrief"):
        config = load_config(str(config_file))

    assert config.settings.digest_mode == "digest"
    assert config.settings.digest_groups == []
    assert "digest mode enabled but no digest_groups configured" in caplog.text


@pytest.mark.unit
def test_load_config_digest_groups_null(tmp_path, mock_env_vars):
    """Test digest_groups: null (YAML key with no value) defaults to empty list."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  digest_groups:
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))
    assert config.settings.digest_groups == []


@pytest.mark.unit
def test_load_config_digest_groups_non_string_fields(tmp_path, mock_env_vars):
    """Test digest_groups with non-string name/description raises ValueError."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  digest_groups:
    - name: 123
      description: "A numeric name"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="must be strings"):
        load_config(str(config_file))


@pytest.mark.unit
def test_load_config_valid_output_languages(tmp_path, mock_env_vars):
    """Test that all supported languages are accepted."""
    for lang in ("English", "Russian", "Spanish", "German", "French"):
        config_content = f"""
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  output_language: "{lang}"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))
        assert config.settings.output_language == lang


@pytest.mark.unit
def test_load_config_invalid_output_language(tmp_path, mock_env_vars):
    """Test that invalid output_language raises ValueError with supported list."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789
  output_language: "Klingon"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Unsupported output_language") as exc_info:
        load_config(str(config_file))

    error_msg = str(exc_info.value)
    assert "Klingon" in error_msg
    for lang in ("English", "Russian", "Spanish", "German", "French"):
        assert lang in error_msg


@pytest.mark.unit
def test_load_config_per_channel_overrides(tmp_path, mock_env_vars):
    """Per-channel lookback_hours and prompt_extra are parsed into ChannelConfig."""
    config_content = """
channels:
  - id: "@jobs"
    name: "Jobs"
    lookback_hours: 72
    prompt_extra: "Focus on backend roles only."
  - id: "@news"
    name: "News"

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))

    jobs, news = config.channels
    assert jobs.lookback_hours == 72
    assert jobs.prompt_extra == "Focus on backend roles only."
    assert news.lookback_hours is None
    assert news.prompt_extra == ""


@pytest.mark.unit
def test_load_config_invalid_lookback_hours_type(tmp_path, mock_env_vars):
    """Non-int lookback_hours raises ValueError."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"
    lookback_hours: "72h"

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="lookback_hours must be an int"):
        load_config(str(config_file))


@pytest.mark.unit
def test_load_config_invalid_lookback_hours_value(tmp_path, mock_env_vars):
    """Non-positive lookback_hours raises ValueError."""
    config_content = """
channels:
  - id: "@test"
    name: "Test"
    lookback_hours: 0

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="lookback_hours must be positive"):
        load_config(str(config_file))


@pytest.mark.unit
def test_load_config_duplicate_channel_names(tmp_path, mock_env_vars):
    """Duplicate channel names raise ValueError to prevent silent override loss."""
    config_content = """
channels:
  - id: "@first"
    name: "Same Name"
  - id: "@second"
    name: "Same Name"

settings:
  target_user_id: 123456789
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)

    with pytest.raises(ValueError, match="Duplicate channel names.*Same Name"):
        load_config(str(config_file))


# ---------------------------------------------------------------------------
# StorageConfig tests
# ---------------------------------------------------------------------------

def _storage_config_file(tmp_path, storage_block: str) -> str:
    content = f"""
channels:
  - id: "@test"
    name: "Test"

settings:
  target_user_id: 123456789

{storage_block}
"""
    p = tmp_path / "config.yaml"
    p.write_text(content)
    return str(p)


@pytest.mark.unit
def test_storage_config_missing_block_defaults(tmp_path, mock_env_vars):
    config = load_config(_storage_config_file(tmp_path, ""))
    assert config.storage == StorageConfig()
    assert config.storage.enabled is False
    assert config.storage.backend == "sqlite"
    assert config.storage.path == "data/messages.db"
    assert config.storage.url == ""


@pytest.mark.unit
def test_storage_config_sqlite_explicit(tmp_path, mock_env_vars):
    block = """
storage:
  enabled: true
  backend: sqlite
  path: /tmp/test.db
"""
    config = load_config(_storage_config_file(tmp_path, block))
    assert config.storage.enabled is True
    assert config.storage.backend == "sqlite"
    assert config.storage.path == "/tmp/test.db"


@pytest.mark.unit
def test_storage_config_postgres_with_url(tmp_path, mock_env_vars):
    block = """
storage:
  enabled: true
  backend: postgres
  url: "postgresql://user:pass@localhost:5432/db"
"""
    config = load_config(_storage_config_file(tmp_path, block))
    assert config.storage.enabled is True
    assert config.storage.backend == "postgres"
    assert config.storage.url == "postgresql://user:pass@localhost:5432/db"


@pytest.mark.unit
def test_storage_config_postgres_enabled_empty_url_raises(tmp_path, mock_env_vars):
    block = """
storage:
  enabled: true
  backend: postgres
  url: ""
"""
    with pytest.raises(ValueError, match="storage.url must be set"):
        load_config(_storage_config_file(tmp_path, block))


@pytest.mark.unit
def test_storage_config_postgres_disabled_empty_url_ok(tmp_path, mock_env_vars):
    block = """
storage:
  enabled: false
  backend: postgres
  url: ""
"""
    config = load_config(_storage_config_file(tmp_path, block))
    assert config.storage.enabled is False


@pytest.mark.unit
def test_storage_config_invalid_backend_raises(tmp_path, mock_env_vars):
    block = """
storage:
  backend: mysql
"""
    with pytest.raises(ValueError, match="storage.backend must be"):
        load_config(_storage_config_file(tmp_path, block))


@pytest.mark.unit
def test_storage_config_enabled_not_bool_raises(tmp_path, mock_env_vars):
    block = """
storage:
  enabled: "yes"
"""
    with pytest.raises(ValueError, match="storage.enabled must be a bool"):
        load_config(_storage_config_file(tmp_path, block))


@pytest.mark.unit
def test_storage_config_empty_path_raises(tmp_path, mock_env_vars):
    block = """
storage:
  path: ""
"""
    with pytest.raises(ValueError, match="storage.path must be a non-empty string"):
        load_config(_storage_config_file(tmp_path, block))
