"""Tests for setup_wizard module."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from dotenv import dotenv_values

from src.config_loader import load_config
from src.setup_wizard import (
    channel_entries,
    login,
    parse_phone,
    parse_selection,
    parse_time,
    parse_timezone,
    render_files,
    write_files,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "text,expected",
    [
        ("1", [0]),
        ("1,4,7-9", [0, 3, 6, 7, 8]),
        (" 2 , 2, 1-2 ", [0, 1]),
        ("10", [9]),
    ],
)
def test_parse_selection_valid(text, expected):
    assert parse_selection(text, 10) == expected


@pytest.mark.unit
@pytest.mark.parametrize("text", ["", ",", "0", "11", "3-1", "a", "1-b", "1--2", "5-12"])
def test_parse_selection_invalid(text):
    with pytest.raises(ValueError):
        parse_selection(text, 10)


@pytest.mark.unit
def test_parse_time_and_timezone():
    assert parse_time("08:00") == "08:00"
    assert parse_timezone("Europe/Berlin") == "Europe/Berlin"
    with pytest.raises(ValueError):
        parse_time("8am")
    with pytest.raises(ValueError):
        parse_timezone("Mars/Base")


@pytest.mark.unit
def test_parse_phone():
    assert parse_phone("+7 999 123-45-67") == "+79991234567"
    with pytest.raises(ValueError, match="bot token"):
        parse_phone("123456789:ABC-DEF")
    with pytest.raises(ValueError):
        parse_phone("call me")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_logs_out_bot_session(tmp_path, monkeypatch):
    clients = []

    def make_client(*_args):
        is_bot = not clients
        client = SimpleNamespace(
            start=AsyncMock(),
            get_me=AsyncMock(return_value=SimpleNamespace(bot=is_bot, id=7, first_name="U")),
            log_out=AsyncMock(),
        )
        clients.append(client)
        return client

    monkeypatch.setattr("src.setup_wizard.TelegramClient", make_client)
    answers = iter(["12345", "hash"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    client, env, user_id = await login(tmp_path / "user")

    assert len(clients) == 2
    clients[0].log_out.assert_awaited_once()
    assert client is clients[1]
    assert user_id == 7
    assert env == {"TELEGRAM_API_ID": "12345", "TELEGRAM_API_HASH": "hash"}


@pytest.mark.unit
def test_channel_entries_suffixes_duplicate_names():
    entries = channel_entries([(-1001, "News"), (-1002, "News"), (-1003, "Tech")])
    assert [e["name"] for e in entries] == ["News (-1001)", "News (-1002)", "Tech"]


@pytest.mark.unit
def test_generated_files_load(tmp_path, monkeypatch):
    env = {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "abc",
        "TELEGRAM_BOT_TOKEN": "1:tok",
        "ANTHROPIC_API_KEY": "sk-ant",
    }
    settings = {
        "ai_provider": "anthropic",
        "ai_model": "claude-x",
        "output_language": "English",
        "schedule_time": "07:30",
        "timezone": "Europe/Berlin",
        "target_user_id": 42,
    }
    channels = channel_entries([(-1001234567890, "Канал"), (-1009, "Group")])

    write_files(tmp_path, render_files(env, channels, settings))

    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "docker-compose.yml").read_text().startswith("services:")
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in dotenv_values(tmp_path / ".env").items():
        monkeypatch.setenv(key, value)

    config = load_config(str(tmp_path / "config.yaml"))

    assert config.settings.target_user_id == 42
    assert [c.id for c in config.channels] == [-1001234567890, -1009]
    assert config.channels[0].name == "Канал"
    assert config.settings.ai_provider == "anthropic"
    assert config.settings.timezone == "Europe/Berlin"
    assert config.anthropic_api_key == "sk-ant"


@pytest.mark.unit
def test_write_files_keeps_existing_on_no(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text("old")
    monkeypatch.setattr("builtins.input", lambda _: "n")

    write_files(tmp_path, {"config.yaml": "new", ".env": "A=1\n"})

    assert (tmp_path / "config.yaml").read_text() == "old"
    assert (tmp_path / ".env").read_text() == "A=1\n"


@pytest.mark.unit
def test_write_files_overwrites_on_yes(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text("old")
    monkeypatch.setattr("builtins.input", lambda _: "y")

    write_files(tmp_path, {"config.yaml": "new"})

    assert (tmp_path / "config.yaml").read_text() == "new"
