"""
Configuration loader for Telebrief.
Loads settings from config.yaml and environment variables.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List

import yaml
from dotenv import load_dotenv


@dataclass
class ChannelConfig:
    """Configuration for a single Telegram channel/chat."""

    id: str | int  # str for @username, int for numeric Telegram channel ID
    name: str
    lookback_hours: int | None = None  # None = use global settings.lookback_hours
    prompt_extra: str = ""  # appended to system prompt when summarizing this channel


@dataclass
class DigestGroupConfig:
    """Configuration for a single digest topic group."""

    name: str
    description: str


@dataclass
class StorageConfig:
    """Configuration for the persistent message storage backend."""

    enabled: bool = False
    backend: str = "sqlite"        # "sqlite" | "postgres"
    path: str = "data/messages.db"
    url: str = field(default="", repr=False)  # postgres only; repr=False prevents credential exposure in logs


@dataclass
class Settings:
    """Application settings."""

    schedule_time: str
    timezone: str
    lookback_hours: int
    openai_model: str
    openai_temperature: float
    temperature: float = 0.7
    max_tokens_per_summary: int = 1500
    use_emojis: bool = True
    include_statistics: bool = True
    target_user_id: int = 0
    auto_cleanup_old_digests: bool = True
    max_messages_per_channel: int = 500
    max_prompt_chars: int = 8000
    api_timeout: int = 30
    ai_provider: str = "openai"
    ai_model: str = ""
    ollama_base_url: str = "http://localhost:11434"
    output_language: str = "Russian"
    digest_mode: str = "channel"
    digest_groups: List[DigestGroupConfig] = field(default_factory=list)


@dataclass
class Config:
    """Complete application configuration."""

    channels: List[ChannelConfig]
    settings: Settings

    # Environment variables
    telegram_api_id: int
    telegram_api_hash: str
    telegram_bot_token: str
    openai_api_key: str
    log_level: str
    anthropic_api_key: str = ""
    storage: StorageConfig = field(default_factory=StorageConfig)


SUPPORTED_LANGUAGES = ("English", "Russian", "Spanish", "German", "French")

_SUPPORTED_PROVIDERS = {"openai", "ollama", "anthropic"}
_PROVIDER_DEFAULT_MODELS = {
    "openai": "gpt-5-nano",
    "anthropic": "claude-sonnet-4-5-20250929",
    "ollama": "llama3",
}


def _resolve_ai_settings(settings_dict: dict) -> tuple:
    """Resolve ai_provider and ai_model from settings dict.

    Returns:
        Tuple of (ai_provider, ai_model)

    Raises:
        ValueError: If ai_provider is unsupported
    """
    raw_provider = settings_dict.get("ai_provider", "openai")
    if not isinstance(raw_provider, str):
        raise ValueError(f"ai_provider must be a string, got {type(raw_provider).__name__}")
    ai_provider = raw_provider.lower()

    if ai_provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported ai_provider: '{ai_provider}'. "
            f"Supported providers: {', '.join(sorted(_SUPPORTED_PROVIDERS))}"
        )

    default_model = _PROVIDER_DEFAULT_MODELS[ai_provider]

    # ai_model takes priority; openai_model is only a fallback for the openai provider
    ai_model = settings_dict.get("ai_model") or (
        settings_dict.get("openai_model", default_model)
        if ai_provider == "openai"
        else default_model
    )

    return ai_provider, ai_model


def _parse_digest_settings(
    settings_dict: dict,
) -> tuple[str, list[DigestGroupConfig], str]:
    """Parse digest_mode, digest_groups, and output_language from settings.

    Returns:
        Tuple of (digest_mode, digest_groups, output_language)
    """
    digest_mode = settings_dict.get("digest_mode", "channel")
    if digest_mode not in ("channel", "digest"):
        raise ValueError(f"Invalid digest_mode: '{digest_mode}'. Must be 'channel' or 'digest'.")

    digest_groups = []
    raw_groups = settings_dict.get("digest_groups") or []
    for i, g in enumerate(raw_groups):
        if not isinstance(g, dict) or "name" not in g or "description" not in g:
            raise ValueError(
                f"digest_groups[{i}] must be a dict with 'name' and 'description' fields"
            )
        if not isinstance(g["name"], str) or not isinstance(g["description"], str):
            raise ValueError(f"digest_groups[{i}] 'name' and 'description' must be strings")
        digest_groups.append(DigestGroupConfig(name=g["name"], description=g["description"]))

    output_language = settings_dict.get("output_language", "Russian")
    if output_language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported output_language: '{output_language}'. "
            f"Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
        )

    if digest_mode == "digest" and not digest_groups:
        logger = logging.getLogger("telebrief")
        logger.warning(
            "digest mode enabled but no digest_groups configured"
            " — all content will go to 'Other'"
        )

    return digest_mode, digest_groups, output_language


def _parse_channel_entry(i: int, ch: object) -> ChannelConfig:
    """Parse and validate a single channel entry from YAML.

    Raises:
        ValueError: If the entry has wrong type, missing required fields, or invalid values
    """
    if not isinstance(ch, dict):
        raise ValueError(f"channels[{i}] must be a mapping, got {type(ch).__name__}")
    for required in ("id", "name"):
        if required not in ch:
            raise ValueError(f"channels[{i}] missing required field '{required}'")
    # id accepts str (username) or int (numeric Telegram ID); name must be a non-empty string
    if not isinstance(ch["name"], str) or not ch["name"].strip():
        raise ValueError(f"channels[{i}].name must be a non-empty string, got {ch['name']!r}")
    if not isinstance(ch["id"], (str, int)) or isinstance(ch["id"], bool):
        raise ValueError(f"channels[{i}].id must be a string or int, got {type(ch['id']).__name__}")
    lookback_hours = ch.get("lookback_hours")
    if lookback_hours is not None:
        if not isinstance(lookback_hours, int) or isinstance(lookback_hours, bool):
            raise ValueError(
                f"channels[{i}].lookback_hours must be an int, "
                f"got {type(lookback_hours).__name__}"
            )
        if lookback_hours <= 0:
            raise ValueError(f"channels[{i}].lookback_hours must be positive, got {lookback_hours}")
    prompt_extra = ch.get("prompt_extra", "")
    if not isinstance(prompt_extra, str):
        raise ValueError(
            f"channels[{i}].prompt_extra must be a string, got {type(prompt_extra).__name__}"
        )
    return ChannelConfig(
        id=ch["id"],
        name=ch["name"],
        lookback_hours=lookback_hours,
        prompt_extra=prompt_extra,
    )


def _parse_storage_config(yaml_config: dict) -> StorageConfig:
    """Parse and validate the optional top-level storage: block.

    Raises:
        ValueError: If any field has wrong type or invalid value.
    """
    raw = yaml_config.get("storage")
    if raw is None:
        return StorageConfig()
    if not isinstance(raw, dict):
        raise ValueError(f"'storage' must be a mapping, got {type(raw).__name__}")

    enabled = raw.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError(f"storage.enabled must be a bool, got {type(enabled).__name__}")

    backend = raw.get("backend", "sqlite")
    if not isinstance(backend, str):
        raise ValueError(f"storage.backend must be a string, got {type(backend).__name__}")
    if backend not in ("sqlite", "postgres"):
        raise ValueError(f"storage.backend must be 'sqlite' or 'postgres', got {backend!r}")

    path = raw.get("path", "data/messages.db")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("storage.path must be a non-empty string")

    url = raw.get("url", "")
    if not isinstance(url, str):
        raise ValueError(f"storage.url must be a string, got {type(url).__name__}")
    if backend == "postgres" and enabled and not url.strip():
        raise ValueError("storage.url must be set when backend is 'postgres' and enabled is true")

    return StorageConfig(enabled=enabled, backend=backend, path=path, url=url)


def _parse_channels(yaml_config: dict) -> List[ChannelConfig]:
    """Parse and validate channel configs from YAML.

    Raises:
        ValueError: If channels list is empty, entries are invalid, or names are duplicated
    """
    if not isinstance(yaml_config, dict):
        raise ValueError(
            f"config.yaml must contain a top-level mapping, got {type(yaml_config).__name__}"
        )
    channels_value = yaml_config.get("channels", [])
    if not isinstance(channels_value, list):
        raise ValueError(
            f"config.yaml field 'channels' must be a list, got {type(channels_value).__name__}"
        )
    channels = [_parse_channel_entry(i, ch) for i, ch in enumerate(channels_value)]

    if not channels:
        raise ValueError("No channels configured in config.yaml")

    seen: set[str] = set()
    duplicates: set[str] = set()
    for c in channels:
        if c.name in seen:
            duplicates.add(c.name)
        seen.add(c.name)
    if duplicates:
        raise ValueError(f"Duplicate channel names in config.yaml: {', '.join(sorted(duplicates))}")

    return channels


def _load_and_validate_env_vars(ai_provider: str) -> dict:
    """Load and validate required environment variables.

    Returns:
        Dict with keys matching Config env var fields.
    """
    telegram_api_id = os.getenv("TELEGRAM_API_ID")
    telegram_api_hash = os.getenv("TELEGRAM_API_HASH")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    missing_vars = []
    if not telegram_api_id:
        missing_vars.append("TELEGRAM_API_ID")
    if not telegram_api_hash:
        missing_vars.append("TELEGRAM_API_HASH")
    if not telegram_bot_token:
        missing_vars.append("TELEGRAM_BOT_TOKEN")

    if ai_provider == "openai" and not openai_api_key:
        missing_vars.append("OPENAI_API_KEY")
    elif ai_provider == "anthropic" and not anthropic_api_key:
        missing_vars.append("ANTHROPIC_API_KEY")

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please set them in .env file (see .env.example)"
        )

    assert telegram_api_id is not None
    assert telegram_api_hash is not None
    assert telegram_bot_token is not None

    return {
        "telegram_api_id": int(telegram_api_id),
        "telegram_api_hash": telegram_api_hash,
        "telegram_bot_token": telegram_bot_token,
        "openai_api_key": openai_api_key,
        "anthropic_api_key": anthropic_api_key,
        "log_level": log_level,
    }


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to config.yaml file

    Returns:
        Config object with all settings

    Raises:
        FileNotFoundError: If config.yaml not found
        ValueError: If required environment variables missing
    """
    # Load environment variables from .env file
    load_dotenv()

    # Load YAML configuration
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f)

    # Parse channels
    channels = _parse_channels(yaml_config)

    # Parse storage config
    storage_config = _parse_storage_config(yaml_config)

    # Parse settings
    settings_dict = yaml_config.get("settings", {})
    ai_provider, ai_model = _resolve_ai_settings(settings_dict)
    digest_mode, digest_groups, output_language = _parse_digest_settings(settings_dict)

    settings = Settings(
        schedule_time=settings_dict.get("schedule_time", "08:00"),
        timezone=settings_dict.get("timezone", "UTC"),
        lookback_hours=settings_dict.get("lookback_hours", 24),
        openai_model=settings_dict.get("openai_model", "gpt-5-nano"),
        openai_temperature=settings_dict.get("openai_temperature", 0.7),
        temperature=settings_dict.get("temperature", settings_dict.get("openai_temperature", 0.7)),
        max_tokens_per_summary=settings_dict.get("max_tokens_per_summary", 1500),
        use_emojis=settings_dict.get("use_emojis", True),
        include_statistics=settings_dict.get("include_statistics", True),
        target_user_id=settings_dict.get("target_user_id", 0),
        auto_cleanup_old_digests=settings_dict.get("auto_cleanup_old_digests", True),
        max_messages_per_channel=settings_dict.get("max_messages_per_channel", 500),
        max_prompt_chars=settings_dict.get("max_prompt_chars", 8000),
        api_timeout=int(settings_dict.get("api_timeout", 30)),
        ai_provider=ai_provider,
        ai_model=ai_model,
        ollama_base_url=settings_dict.get("ollama_base_url", "http://localhost:11434"),
        output_language=output_language,
        digest_mode=digest_mode,
        digest_groups=digest_groups,
    )

    if settings.target_user_id == 0:
        raise ValueError(
            "target_user_id not configured in config.yaml. "
            "Get your Telegram user ID from @userinfobot"
        )

    env_vars = _load_and_validate_env_vars(ai_provider)

    return Config(
        channels=channels,
        settings=settings,
        storage=storage_config,
        **env_vars,
    )


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = load_config()
        print("✅ Configuration loaded successfully!")
        print(f"Channels: {len(config.channels)}")
        print(f"Target user: {config.settings.target_user_id}")
        print(f"AI provider: {config.settings.ai_provider}, model: {config.settings.ai_model}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
