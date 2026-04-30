from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.collector import Message
from src.config_loader import ChannelConfig
from src.extensions.filters import KeywordFilter, MessageFilter, MinLengthFilter, RegexFilter


def _make_message(text: str) -> Message:
    return Message(
        text=text,
        sender="user",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        link="https://t.me/c/1",
        channel_name="test",
        has_media=False,
        media_type="",
    )


def _channel() -> ChannelConfig:
    return ChannelConfig(id="@test", name="test")


# --- Protocol conformance ---


def test_keyword_filter_is_message_filter():
    assert isinstance(KeywordFilter(), MessageFilter)


def test_regex_filter_is_message_filter():
    assert isinstance(RegexFilter(pattern="x"), MessageFilter)


def test_min_length_filter_is_message_filter():
    assert isinstance(MinLengthFilter(min_chars=5), MessageFilter)


# --- KeywordFilter ---


@pytest.mark.asyncio
async def test_keyword_include_match():
    f = KeywordFilter(include=["job"])
    msgs = [_make_message("new job offer"), _make_message("unrelated text")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1
    assert result[0].text == "new job offer"


@pytest.mark.asyncio
async def test_keyword_include_case_insensitive():
    f = KeywordFilter(include=["JOB"])
    msgs = [_make_message("great Job opportunity")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_keyword_exclude_removes_message():
    f = KeywordFilter(exclude=["nsfw"])
    msgs = [_make_message("clean content"), _make_message("nsfw material")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1
    assert result[0].text == "clean content"


@pytest.mark.asyncio
async def test_keyword_include_and_exclude():
    f = KeywordFilter(include=["job"], exclude=["spam"])
    msgs = [
        _make_message("job listing here"),
        _make_message("job spam alert"),
        _make_message("unrelated"),
    ]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1
    assert result[0].text == "job listing here"


@pytest.mark.asyncio
async def test_keyword_empty_input():
    f = KeywordFilter(include=["job"])
    result = await f.filter(_channel(), [])
    assert result == []


@pytest.mark.asyncio
async def test_keyword_no_include_no_exclude_passes_all():
    f = KeywordFilter()
    msgs = [_make_message("anything"), _make_message("whatever")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 2


# --- RegexFilter ---


@pytest.mark.asyncio
async def test_regex_include_mode_match():
    f = RegexFilter(pattern=r"\d{4}", mode="include")
    msgs = [_make_message("price 1234 usd"), _make_message("no digits here")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1
    assert result[0].text == "price 1234 usd"


@pytest.mark.asyncio
async def test_regex_exclude_mode_removes_matching():
    f = RegexFilter(pattern=r"http\S+", mode="exclude")
    msgs = [_make_message("visit https://example.com"), _make_message("plain text")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1
    assert result[0].text == "plain text"


@pytest.mark.asyncio
async def test_regex_empty_input():
    f = RegexFilter(pattern=r"x")
    result = await f.filter(_channel(), [])
    assert result == []


@pytest.mark.asyncio
async def test_regex_no_match_include_mode_returns_empty():
    f = RegexFilter(pattern=r"xyz123nothere", mode="include")
    msgs = [_make_message("hello world")]
    result = await f.filter(_channel(), msgs)
    assert result == []


@pytest.mark.asyncio
async def test_regex_default_mode_is_include():
    f = RegexFilter(pattern=r"hello")
    msgs = [_make_message("hello world"), _make_message("bye")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1


# --- MinLengthFilter ---


@pytest.mark.asyncio
async def test_min_length_keeps_long_enough():
    f = MinLengthFilter(min_chars=5)
    msgs = [_make_message("hi"), _make_message("hello world")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1
    assert result[0].text == "hello world"


@pytest.mark.asyncio
async def test_min_length_exact_boundary_kept():
    f = MinLengthFilter(min_chars=5)
    msgs = [_make_message("hello")]  # exactly 5 chars
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_min_length_empty_text_dropped():
    f = MinLengthFilter(min_chars=1)
    msgs = [_make_message(""), _make_message("x")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 1
    assert result[0].text == "x"


@pytest.mark.asyncio
async def test_min_length_empty_input():
    f = MinLengthFilter(min_chars=10)
    result = await f.filter(_channel(), [])
    assert result == []


@pytest.mark.asyncio
async def test_min_length_zero_keeps_all():
    f = MinLengthFilter(min_chars=0)
    msgs = [_make_message(""), _make_message("x"), _make_message("long message")]
    result = await f.filter(_channel(), msgs)
    assert len(result) == 3
