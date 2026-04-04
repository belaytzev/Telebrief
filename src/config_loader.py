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

    id: str
    name: str


@dataclass
class DigestGroupConfig:
    """Configuration for a single digest topic group."""

    name: str
    description: str


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
    channels = [
        ChannelConfig(id=ch["id"], name=ch["name"]) for ch in yaml_config.get("channels", [])
    ]

    if not channels:
        raise ValueError("No channels configured in config.yaml")

    # Parse settings
    settings_dict = yaml_config.get("settings", {})
    ai_provider, ai_model = _resolve_ai_settings(settings_dict)

    # Parse digest settings
    digest_mode = settings_dict.get("digest_mode", "channel")
    if digest_mode not in ("channel", "digest"):
        raise ValueError(
            f"Invalid digest_mode: '{digest_mode}'. Must be 'channel' or 'digest'."
        )

    digest_groups = [
        DigestGroupConfig(name=g["name"], description=g["description"])
        for g in settings_dict.get("digest_groups", [])
    ]

    if digest_mode == "digest" and not digest_groups:
        logger = logging.getLogger("telebrief")
        logger.warning(
            "digest mode enabled but no digest_groups configured"
            " — all content will go to 'Other'"
        )

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
        output_language=settings_dict.get("output_language", "Russian"),
        digest_mode=digest_mode,
        digest_groups=digest_groups,
    )

    if settings.target_user_id == 0:
        raise ValueError(
            "target_user_id not configured in config.yaml. "
            "Get your Telegram user ID from @userinfobot"
        )

    # Load environment variables
    telegram_api_id = os.getenv("TELEGRAM_API_ID")
    telegram_api_hash = os.getenv("TELEGRAM_API_HASH")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    # Validate required environment variables
    missing_vars = []
    if not telegram_api_id:
        missing_vars.append("TELEGRAM_API_ID")
    if not telegram_api_hash:
        missing_vars.append("TELEGRAM_API_HASH")
    if not telegram_bot_token:
        missing_vars.append("TELEGRAM_BOT_TOKEN")

    # Validate API key for the selected provider
    if ai_provider == "openai" and not openai_api_key:
        missing_vars.append("OPENAI_API_KEY")
    elif ai_provider == "anthropic" and not anthropic_api_key:
        missing_vars.append("ANTHROPIC_API_KEY")

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please set them in .env file (see .env.example)"
        )

    # Create complete config
    # Type assertions: variables are validated above
    assert telegram_api_id is not None
    assert telegram_api_hash is not None
    assert telegram_bot_token is not None

    config = Config(
        channels=channels,
        settings=settings,
        telegram_api_id=int(telegram_api_id),
        telegram_api_hash=telegram_api_hash,
        telegram_bot_token=telegram_bot_token,
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key,
        log_level=log_level,
    )

    return config


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
