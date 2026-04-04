"""Tests for ui_strings module."""

import pytest

from src.ui_strings import get_ui_strings

# All keys that every supported language must provide
REQUIRED_KEYS = [
    # formatter.py
    "daily_digest",
    "overview",
    "stats_header",
    "channels",
    "messages_processed",
    "digest_for",
    "period_last_hours",
    "messages_count",
    "last_hours",
    "truncated",
    "digest_completed",
    "channels_processed",
    "total_messages",
    "period",
    # bot_commands.py
    "cmd_start_desc",
    "cmd_digest_desc",
    "cmd_cleanup_desc",
    "cmd_status_desc",
    "cmd_help_desc",
    "generating_digest",
    "digest_done",
    "digest_error",
    "digest_exception",
    "cleaning_up",
    "cleanup_done",
    "cleanup_partial",
    "cleanup_error",
    "status_header",
    "provider_label",
    "model_label",
    "channels_configured",
    "auto_cleanup_label",
    "enabled",
    "disabled",
    "next_digest",
    "scheduler_not_running",
    "available_commands",
    "help_title",
    "help_intro",
    "help_commands_header",
    "help_auto_mode",
    "help_auto_desc",
    "help_features",
    "help_features_list",
    # digest grouper
    "group_other",
    "group_items_count",
    "groups_processed",
    "from_channel",
    # formatter (open channel link)
    "open_channel",
    # bot_commands (rate limiting)
    "rate_limited",
]

SUPPORTED_LANGUAGES = ["English", "Russian", "Spanish", "German", "French"]


@pytest.mark.unit
def test_get_ui_strings_english():
    """English returns English strings for key labels."""
    s = get_ui_strings("English")

    assert s["daily_digest"] == "Daily Digest"
    assert s["overview"] == "Brief Overview"
    assert s["stats_header"] == "Statistics"
    assert s["enabled"] == "Enabled"
    assert s["disabled"] == "Disabled"
    assert s["digest_completed"] == "Digest completed"
    assert s["channels_processed"] == "Channels processed"
    assert s["total_messages"] == "Total messages"
    assert s["period"] == "Period"


@pytest.mark.unit
def test_get_ui_strings_russian():
    """Russian returns Russian strings for key labels."""
    s = get_ui_strings("Russian")

    assert s["daily_digest"] == "Ежедневный дайджест"
    assert s["overview"] == "Краткий обзор"
    assert s["stats_header"] == "Статистика"
    assert s["enabled"] == "Включена"
    assert s["disabled"] == "Выключена"
    assert s["digest_completed"] == "Дайджест завершён"
    assert s["channels_processed"] == "Обработано каналов"
    assert s["total_messages"] == "Всего сообщений"
    assert s["period"] == "Период"


@pytest.mark.unit
def test_get_ui_strings_unknown_language_falls_back_to_english():
    """Unsupported language falls back to English strings."""
    s = get_ui_strings("Japanese")

    assert s["daily_digest"] == "Daily Digest"
    assert s["enabled"] == "Enabled"
    assert s["disabled"] == "Disabled"
    assert s["digest_completed"] == "Digest completed"


@pytest.mark.unit
@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_all_required_keys_present_for_each_language(language):
    """Every supported language provides all required keys."""
    s = get_ui_strings(language)
    for key in REQUIRED_KEYS:
        assert key in s, f"Missing key '{key}' for language '{language}'"


@pytest.mark.unit
@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_no_empty_strings_for_any_language(language):
    """No key maps to an empty string in any supported language."""
    s = get_ui_strings(language)
    for key in REQUIRED_KEYS:
        assert s[key], f"Empty value for key '{key}' in language '{language}'"


@pytest.mark.unit
@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_digest_group_keys_present_for_each_language(language):
    """Every supported language provides all digest group keys."""
    s = get_ui_strings(language)
    digest_keys = ["group_other", "group_items_count", "groups_processed", "from_channel"]
    for key in digest_keys:
        assert key in s, f"Missing digest key '{key}' for language '{language}'"
        assert s[key], f"Empty value for digest key '{key}' in language '{language}'"


@pytest.mark.unit
def test_digest_group_keys_english_values():
    """English digest group keys have expected values."""
    s = get_ui_strings("English")
    assert s["group_other"] == "Other"
    assert s["group_items_count"] == "{count} items"
    assert s["groups_processed"] == "Groups"
    assert s["from_channel"] == "from {channel}"


@pytest.mark.unit
def test_get_ui_strings_returns_dict():
    """get_ui_strings always returns a dict."""
    assert isinstance(get_ui_strings("English"), dict)
    assert isinstance(get_ui_strings("Unknown"), dict)
