"""
AI-powered summarizer using pluggable providers with configurable output language.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from src.ai_providers import AIProvider, TokenBudgetExhaustedError, create_provider
from src.collector import Message
from src.config_loader import ChannelConfig, Config, DigestGroupConfig
from src.extensions.loader import load_class
from src.extensions.prompts import DefaultComposer, PromptComposer
from src.xml_escape import escape_xml_delimiters

ERROR_SUMMARY_PREFIX = "Error processing channel"
MAX_SUMMARY_CHARS = 3500
_MINOR_OVERAGE_CHARS = 200  # truncate directly without retry for small overages


def _load_base_template(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {path!r}. "
            "Use an absolute path or a path relative to the working directory."
        )
    return p.read_text(encoding="utf-8")


_DEFAULT_TEMPLATE_PATH = str(Path(__file__).parent / "prompts" / "base_summary.txt")


def __getattr__(name: str) -> str:
    # Lazy module attribute: read template only when accessed, keeping import side-effect free.
    if name == "SYSTEM_PROMPT_TEMPLATE":
        return _load_base_template(_DEFAULT_TEMPLATE_PATH)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class Summarizer:
    """Generates AI-powered summaries using a pluggable AI provider."""

    def __init__(self, config: Config, logger: logging.Logger):
        """
        Initialize summarizer.

        Args:
            config: Application configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.provider: AIProvider = create_provider(
            provider_name=config.settings.ai_provider,
            logger=logger,
            openai_api_key=config.openai_api_key,
            anthropic_api_key=config.anthropic_api_key,
            ollama_base_url=config.settings.ollama_base_url,
            api_timeout=config.settings.api_timeout,
        )
        self.model = config.settings.ai_model
        self.temperature = config.settings.temperature
        self.max_tokens = config.settings.max_tokens_per_summary
        self.output_language = config.settings.output_language
        self._channels_by_name = {ch.name: ch for ch in config.channels}

        # Resolve template path; use absolute bundled default when config holds the sentinel value
        template_path = (
            _DEFAULT_TEMPLATE_PATH
            if config.prompts.base_template == "src/prompts/base_summary.txt"
            else config.prompts.base_template
        )
        base_template = _load_base_template(template_path)

        # Build channel-to-group lookup for prompt composition
        groups_by_name: dict[str, DigestGroupConfig] = {
            g.name: g for g in config.settings.digest_groups
        }
        self._channel_to_group: dict[str, DigestGroupConfig | None] = {
            ch.name: groups_by_name.get(ch.group) if ch.group else None for ch in config.channels
        }

        # Instantiate composer (custom dotted-path or built-in DefaultComposer)
        if config.prompts.composer:
            composer_cls = load_class(config.prompts.composer)
            try:
                self._composer: PromptComposer = composer_cls(base_template, self.output_language)
            except TypeError as exc:
                raise TypeError(
                    f"Custom PromptComposer {config.prompts.composer!r} must accept "
                    "(base_template: str, language: str) as constructor arguments. "
                    f"Original error: {exc}"
                ) from exc
            if not isinstance(self._composer, PromptComposer) or not callable(
                getattr(self._composer, "compose", None)
            ):
                raise TypeError(
                    f"Custom composer {config.prompts.composer!r} does not implement "
                    "PromptComposer (missing or non-callable .compose() method)"
                )
        else:
            self._composer = DefaultComposer(base_template, self.output_language)

    async def summarize_all(self, messages_by_channel: Dict[str, List[Message]]) -> Dict[str, Any]:
        """
        Generate complete digest with per-channel summaries.

        Args:
            messages_by_channel: Messages grouped by channel

        Returns:
            Dictionary with 'channel_summaries' and 'overview' (empty string)
        """
        self.logger.info("Starting summarization process")

        # Filter out empty channels
        non_empty_channels = {name: msgs for name, msgs in messages_by_channel.items() if msgs}

        if not non_empty_channels:
            self.logger.warning("No messages to summarize")
            return {"channel_summaries": {}, "overview": ""}

        # Generate per-channel summaries
        self.logger.info(f"Generating summaries for {len(non_empty_channels)} channels")
        channel_summaries = await self._summarize_per_channel(non_empty_channels)

        return {"channel_summaries": channel_summaries, "overview": ""}

    async def _summarize_per_channel(
        self, messages_by_channel: Dict[str, List[Message]]
    ) -> Dict[str, str]:
        """
        Generate summary for each channel.

        Args:
            messages_by_channel: Messages grouped by channel

        Returns:
            Dictionary mapping channel names to summaries
        """
        summaries = {}

        for channel_name, messages in messages_by_channel.items():
            try:
                summary = await self._summarize_channel(channel_name, messages)
                summaries[channel_name] = summary
                self.logger.info(f"Summarized {channel_name}")
            except Exception as e:
                self.logger.error(f"Failed to summarize {channel_name}: {e}")
                summaries[channel_name] = f"{ERROR_SUMMARY_PREFIX}: {str(e)}"

        return summaries

    async def _summarize_channel(self, channel_name: str, messages: List[Message]) -> str:
        """
        Generate summary for a single channel.

        Args:
            channel_name: Name of the channel
            messages: List of messages

        Returns:
            Summary in the configured output language
        """
        # Format messages for prompt
        original_count = len(messages)
        messages_text = self._format_messages_for_prompt(
            messages, max_chars=self.config.settings.max_prompt_chars
        )
        actual_count = len(messages_text.splitlines()) if messages_text else 0

        truncation_note = ""
        if actual_count < original_count:
            dropped = original_count - actual_count
            truncation_note = (
                f"\nNOTE: Only the {actual_count} most recent messages are shown below; "
                f"{dropped} older message(s) were excluded due to input size limits "
                f"and are NOT part of this digest.\n"
            )

        prompt = f"""
Analyze the following messages from Telegram channel "{channel_name}" \
and create a concise summary.

CRITICAL - LENGTH CONSTRAINT:
- Telegram has a 4096 character limit per message
- Your summary MUST be NO MORE than 3500 characters (including emojis and formatting)
- This is a hard limit - if exceeded, the message will not be delivered
- Move lower-priority posts to the 📎 Also: section rather than dropping them
{truncation_note}
Focus on covering ALL messages shown below — no message in this list should be silently dropped.

Response format (TWO sections):

SECTION 1 — Full summaries (most important posts, you decide how many):
- 1-2 sentences per bullet, max 150-200 characters each
- Emoji at the start of each bullet
- Be concise but informative

SECTION 2 — 📎 Also: (all remaining posts not covered in Section 1)
- One line per post: • Brief subject [→ link] (omit [→ link] if no link in input for that message)
- Use the exact link provided in the input (after the last " | "); if no " | " present, omit the link bracket
- If there are no remaining posts, omit this section entirely

Messages (total: {actual_count}):
<channel_messages>
{escape_xml_delimiters(messages_text)}
</channel_messages>
"""

        channel_cfg = self._channels_by_name.get(channel_name)
        group_cfg = self._channel_to_group.get(channel_name)
        if channel_cfg is not None:
            system_prompt = self._composer.compose(channel_cfg, group_cfg)
        else:
            self.logger.warning(f"Channel {channel_name!r} not in config; using default prompt")
            system_prompt = self._composer.compose(
                ChannelConfig(id=channel_name, name=channel_name), None
            )
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        summary = await self._call_ai_with_retry(channel_name, chat_messages)
        summary = await self._enforce_length_limit(channel_name, summary, chat_messages)

        self.logger.debug(f"Summary for {channel_name}: {len(summary)} chars")
        return summary

    async def _call_ai_with_retry(self, channel_name: str, chat_messages: list) -> str:
        """Call AI provider, retrying with higher token budget on exhaustion."""
        try:
            return await self.provider.chat_completion(
                messages=chat_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except TokenBudgetExhaustedError:
            retry_max_tokens = self.max_tokens * 3
            self.logger.warning(
                "Token budget exhausted for %s; retrying with max_tokens=%d",
                channel_name,
                retry_max_tokens,
            )
            try:
                return await self.provider.chat_completion(
                    messages=chat_messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=retry_max_tokens,
                    reasoning_effort="low",
                )
            except Exception as retry_exc:
                self.logger.error(
                    "Retry also failed for %s (max_tokens=%d): %s",
                    channel_name,
                    retry_max_tokens,
                    retry_exc,
                )
                raise
        except Exception as e:
            self.logger.error(f"AI provider error for {channel_name}: {e}")
            raise

    async def _enforce_length_limit(
        self, channel_name: str, summary: str, chat_messages: list
    ) -> str:
        """Request shorter summary if over limit, truncate as last resort."""
        if len(summary) <= MAX_SUMMARY_CHARS:
            return summary

        overage = len(summary) - MAX_SUMMARY_CHARS
        if overage <= _MINOR_OVERAGE_CHARS:
            summary = self._truncate_at_sentence_boundary(summary, MAX_SUMMARY_CHARS)
            self.logger.warning(
                "Summary for %s is %d chars (limit %d, overage %d), truncated at sentence boundary",
                channel_name,
                len(summary),
                MAX_SUMMARY_CHARS,
                overage,
            )
            return summary

        self.logger.warning(
            "Summary for %s is %d chars (limit %d), requesting shorter version",
            channel_name,
            len(summary),
            MAX_SUMMARY_CHARS,
        )
        retry_messages = chat_messages + [
            {"role": "assistant", "content": summary},
            {
                "role": "user",
                "content": (
                    f"Your response was {len(summary)} characters. "
                    f"Shorten to under {MAX_SUMMARY_CHARS} characters."
                ),
            },
        ]
        try:
            summary = await self.provider.chat_completion(
                messages=retry_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            self.logger.error("Length-reduction retry failed for %s: %s", channel_name, e)

        if len(summary) > MAX_SUMMARY_CHARS:
            summary = self._truncate_at_sentence_boundary(summary, MAX_SUMMARY_CHARS)
            self.logger.warning(
                "Summary for %s still over limit after retry, "
                "truncated to %d chars at sentence boundary",
                channel_name,
                len(summary),
            )
        return summary

    @staticmethod
    def _truncate_at_sentence_boundary(text: str, max_chars: int) -> str:
        """Truncate text at the last complete sentence within max_chars."""
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        # Find the last sentence-ending punctuation
        last_period = -1
        for i in range(len(truncated) - 1, -1, -1):
            if truncated[i] in ".!?":
                last_period = i
                break
        if last_period > 0:
            return truncated[: last_period + 1]
        # No sentence boundary found — hard truncate
        return truncated

    def _format_messages_for_prompt(self, messages: List[Message], max_chars: int = 8000) -> str:
        """
        Format messages for inclusion in prompt, keeping the most recent ones within budget.

        Args:
            messages: List of messages (oldest-first)
            max_chars: Maximum total characters of the returned string

        Returns:
            Formatted string with the most recent messages that fit within max_chars
        """
        formatted = []
        for i, msg in enumerate(messages, 1):
            timestamp = msg.timestamp.strftime("%H:%M")
            text = (
                (msg.text[:500] if len(msg.text) > 500 else msg.text)
                .replace("\r", " ")
                .replace("\n", " ")
                .replace(" | ", " - ")
            )
            sender = msg.sender.replace("\r", " ").replace("\n", " ").replace(" | ", " - ")
            link = msg.link if msg.link and msg.link != "#" else ""
            link_part = f" | {link}" if link else ""
            formatted.append(f"{i}. [{timestamp}] {sender}: {text}{link_part}")

        # Select most recent messages that fit within the character budget.
        # Always include at least one message (the most recent).
        selected: List[str] = []
        total = 0
        for line in reversed(formatted):
            added_len = len(line) + (1 if selected else 0)  # +1 for the \n separator
            if total + added_len > max_chars and selected:
                break
            selected.append(line)
            total += added_len

        if len(selected) < len(formatted):
            self.logger.warning(
                "Prompt input truncated: kept %d/%d messages (%d chars) "
                "to fit max_prompt_chars=%d. Oldest messages were dropped.",
                len(selected),
                len(formatted),
                total,
                max_chars,
            )

        # Re-number from 1 so the AI sees a clean 1..N sequence regardless of truncation.
        ordered = list(reversed(selected))
        renumbered = []
        for new_i, line in enumerate(ordered, 1):
            dot_pos = line.find(". ")
            if dot_pos == -1:
                renumbered.append(f"{new_i}. {line}")
            else:
                renumbered.append(f"{new_i}{line[dot_pos:]}")
        return "\n".join(renumbered)


async def main():
    """Test summarizer."""
    from src.collector import MessageCollector
    from src.config_loader import load_config
    from src.utils import setup_logging

    config = load_config()
    logger = setup_logging(config.log_level)

    # Collect messages
    collector = MessageCollector(config, logger)
    await collector.connect()
    messages = await collector.fetch_messages(hours=24)
    await collector.disconnect()

    # Summarize
    summarizer = Summarizer(config, logger)
    result = await summarizer.summarize_all(messages)

    print("\n" + "=" * 50)
    print("OVERVIEW:")
    print("=" * 50)
    print(result["overview"])

    print("\n" + "=" * 50)
    print("CHANNEL SUMMARIES:")
    print("=" * 50)
    for channel, summary in result["channel_summaries"].items():
        print(f"\n{channel}:")
        print(summary)


if __name__ == "__main__":
    asyncio.run(main())
