from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.collector import Message
    from src.config_loader import ChannelConfig


@runtime_checkable
class MessageFilter(Protocol):
    name: str

    async def filter(
        self, channel: ChannelConfig, messages: list[Message]
    ) -> list[Message]: ...  # noqa: E704


class KeywordFilter:
    """Keep messages that contain any include keyword and none of the exclude keywords."""

    name = "keyword"

    def __init__(self, include: list[str] | None = None, exclude: list[str] | None = None) -> None:
        self._include = [kw.lower() for kw in (include or [])]
        self._exclude = [kw.lower() for kw in (exclude or [])]

    async def filter(self, channel: ChannelConfig, messages: list[Message]) -> list[Message]:
        result = []
        for msg in messages:
            text = (msg.text or "").lower()
            if self._include and not any(kw in text for kw in self._include):
                continue
            if any(kw in text for kw in self._exclude):
                continue
            result.append(msg)
        return result


class RegexFilter:
    """Keep or drop messages based on a compiled regex pattern."""

    name = "regex"

    def __init__(self, pattern: str, mode: Literal["include", "exclude"] = "include") -> None:
        if mode not in ("include", "exclude"):
            raise ValueError(f"RegexFilter mode must be 'include' or 'exclude', got {mode!r}")
        self._re = re.compile(pattern)
        self._mode = mode

    async def filter(self, channel: ChannelConfig, messages: list[Message]) -> list[Message]:
        result = []
        for msg in messages:
            matched = bool(self._re.search(msg.text or ""))
            if self._mode == "include" and matched:
                result.append(msg)
            elif self._mode == "exclude" and not matched:
                result.append(msg)
        return result


class MinLengthFilter:
    """Drop messages shorter than min_chars characters."""

    name = "min_length"

    def __init__(self, min_chars: int) -> None:
        if min_chars < 0:
            raise ValueError(f"min_chars must be >= 0, got {min_chars}")
        self._min_chars = min_chars

    async def filter(self, channel: ChannelConfig, messages: list[Message]) -> list[Message]:
        return [msg for msg in messages if len(msg.text or "") >= self._min_chars]
