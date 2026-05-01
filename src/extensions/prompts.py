from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.config_loader import ChannelConfig, DigestGroupConfig


@runtime_checkable
class PromptComposer(Protocol):
    def compose(  # noqa: E704
        self, channel: ChannelConfig, group: DigestGroupConfig | None
    ) -> str: ...


class DefaultComposer:
    """Compose system prompts from base template, group extra, and channel extra."""

    def __init__(self, base_template: str, language: str) -> None:
        self._base = base_template
        self._language = language

    def compose(self, channel: ChannelConfig, group: DigestGroupConfig | None) -> str:
        def sub(text: str) -> str:
            return text.replace("{language}", self._language)

        parts = [sub(self._base)]
        if group is not None:
            group_extra = group.prompt_extra
            if group_extra:
                parts.append(sub(group_extra))
        if channel.prompt_extra:
            parts.append(sub(channel.prompt_extra))
        return "\n\n".join(parts)
