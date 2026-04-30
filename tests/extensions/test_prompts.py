from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.config_loader import ChannelConfig
from src.extensions.prompts import DefaultComposer, PromptComposer

BASE = "You are an assistant. Write in {language}."
LANG = "English"


def _channel(prompt_extra: str = "") -> ChannelConfig:
    return ChannelConfig(id="@test", name="test", prompt_extra=prompt_extra)


def _group(prompt_extra: str = "") -> SimpleNamespace:
    return SimpleNamespace(name="TestGroup", description="desc", prompt_extra=prompt_extra)


# --- Protocol conformance ---


def test_default_composer_is_prompt_composer():
    assert isinstance(DefaultComposer(BASE, LANG), PromptComposer)


# --- Base only ---


def test_base_only_no_group_no_channel_extra():
    c = DefaultComposer(BASE, LANG)
    result = c.compose(_channel(), None)
    assert result == "You are an assistant. Write in English."


# --- Language substitution ---


def test_language_substituted():
    c = DefaultComposer(BASE, "Russian")
    result = c.compose(_channel(), None)
    assert "Russian" in result
    assert "{language}" not in result


def test_language_substituted_only_in_base():
    c = DefaultComposer(BASE, LANG)
    channel = _channel(prompt_extra="Extra for {language}.")
    result = c.compose(channel, None)
    # base substituted, channel extra appended verbatim
    assert result.startswith("You are an assistant. Write in English.")
    assert "Extra for {language}." in result


# --- Base + channel ---


def test_base_plus_channel_extra():
    c = DefaultComposer(BASE, LANG)
    channel = _channel(prompt_extra="Focus on tech news.")
    result = c.compose(channel, None)
    assert result == "You are an assistant. Write in English.\n\nFocus on tech news."


# --- Base + group ---


def test_base_plus_group_extra():
    c = DefaultComposer(BASE, LANG)
    group = _group(prompt_extra="Summarize jobs only.")
    result = c.compose(_channel(), group)
    assert result == "You are an assistant. Write in English.\n\nSummarize jobs only."


# --- Base + group + channel ordering ---


def test_base_plus_group_plus_channel_ordering():
    c = DefaultComposer(BASE, LANG)
    group = _group(prompt_extra="Group extra.")
    channel = _channel(prompt_extra="Channel extra.")
    result = c.compose(channel, group)
    parts = result.split("\n\n")
    assert len(parts) == 3
    assert parts[0] == "You are an assistant. Write in English."
    assert parts[1] == "Group extra."
    assert parts[2] == "Channel extra."


# --- Missing group ---


def test_missing_group_none():
    c = DefaultComposer(BASE, LANG)
    result = c.compose(_channel(prompt_extra="Chan."), None)
    assert result == "You are an assistant. Write in English.\n\nChan."


# --- Missing prompt_extra fields ---


def test_empty_group_extra_skipped():
    c = DefaultComposer(BASE, LANG)
    group = _group(prompt_extra="")
    result = c.compose(_channel(), group)
    assert result == "You are an assistant. Write in English."
    assert "\n\n" not in result


def test_empty_channel_extra_skipped():
    c = DefaultComposer(BASE, LANG)
    result = c.compose(_channel(prompt_extra=""), None)
    assert result == "You are an assistant. Write in English."
    assert "\n\n" not in result


def test_group_without_prompt_extra_attr():
    c = DefaultComposer(BASE, LANG)
    # group object with no prompt_extra attribute at all
    group = SimpleNamespace(name="G", description="d")
    result = c.compose(_channel(), group)
    assert result == "You are an assistant. Write in English."


# --- Multiple language placeholders ---


def test_multiple_language_placeholders_all_replaced():
    template = "Write in {language}. Only {language} output."
    c = DefaultComposer(template, "German")
    result = c.compose(_channel(), None)
    assert result == "Write in German. Only German output."
