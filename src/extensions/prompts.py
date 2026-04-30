from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.config_loader import ChannelConfig, DigestGroupConfig


@runtime_checkable
class PromptComposer(Protocol):
    def compose(
        self, channel: ChannelConfig, group: DigestGroupConfig | None
    ) -> str: ...  # noqa: E704


class DefaultComposer:
    """Compose system prompts from base template, group extra, and channel extra."""

    def __init__(self, base_template: str, language: str) -> None:
        self._base = base_template
        self._language = language

    def compose(self, channel: ChannelConfig, group: DigestGroupConfig | None) -> str:
        parts = [self._base.replace("{language}", self._language)]
        if group is not None:
            group_extra = getattr(group, "prompt_extra", "")
            if group_extra:
                parts.append(group_extra)
        if channel.prompt_extra:
            parts.append(channel.prompt_extra)
        return "\n\n".join(parts)
