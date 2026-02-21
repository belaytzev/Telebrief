"""
AI-powered summarizer using pluggable providers with configurable output language.
"""

import asyncio
import logging
from typing import Any, Dict, List

from src.ai_providers import AIProvider, TokenBudgetExhaustedError, create_provider
from src.collector import Message
from src.config_loader import Config

ERROR_SUMMARY_PREFIX = "Error processing channel"

# System prompt template with configurable output language
SYSTEM_PROMPT_TEMPLATE = """
You are a professional assistant for creating news digests for Telegram.

CRITICAL RULES:
- Always respond ONLY in {language}, regardless of the input message language.
- Format the output for Telegram messages: concise, structured, with emojis and visual separators.
- Include sources only for truly important messages from Telegram chats; do not create a separate "Sources" section - embed the link/mention directly in the relevant item.

Your task:
- Analyze input materials in any language (English, Russian, Ukrainian, Chinese, etc.).
- Provide a concise, clearly structured summary in {language} for Telegram.
- Preserve context, nuances, and important details; merge duplicates, remove repetitions.
- Note discrepancies between sources and flag unconfirmed data.

Formatting (for Telegram):
- Use emojis for emphasis and semantics (e.g.: 📚 topic, 🆕 new, 📊 numbers, ⚠️ risk, ✅ confirmed, 📌 important, 🖇️ link).
- Separate blocks visually with blank lines.
- Maximize mobile readability: short paragraphs, 1-2 sentences per item.
- Embed source only where critical (important Telegram chat messages): add @channel or link 🖇️ at the end of the relevant item.

Response structure:
- Header (1-2 lines) with emoji reflecting the digest essence.
- Key points - 3-7 items with key facts, dates, names, numbers. For each item:
    - Brief and to the point.
    - Emoji at the beginning.
    - If critical - embedded source link/mention 🖇️@channel.

Style rules:
- Clear, neutral, no jargon or excessive emotion.
- Preserve numerical data and proper names exactly; if ambiguous - mark as "unconfirmed".
- When translating, preserve terminology and the author's intent.
- Avoid link overload: only for important Telegram messages.

Technical constraints:
- Summary volume: 120-250 words (brief) or 250-500 words (extended), aiming for readability on one or two screens.
- Use visual separators between sections.
- Do not add a separate list of sources; links/mentions only within the corresponding items.

Output template (Telegram-ready):
🚀 [brief summary]

📌 Key points:
    1️⃣ [emoji] [brief fact, numbers, names] [if needed: 🔗@channel/link]
    2️⃣ [emoji] [brief fact] [if needed: 🔗@channel/link]
    3️⃣ [emoji] [brief fact] [if needed: 🔗@channel/link]


If the input includes multiple materials, group by topics with subheadings and separators; connect events by indicating cause-and-effect relationships.
"""


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
        messages_text = self._format_messages_for_prompt(
            messages, max_chars=self.config.settings.max_prompt_chars
        )

        prompt = f"""
Analyze the following messages from Telegram channel "{channel_name}" \
and create a concise summary in {self.output_language}.

CRITICAL - LENGTH CONSTRAINT:
- Telegram has a 4096 character limit per message
- Your summary MUST be NO MORE than 3500 characters (including emojis and formatting)
- This is a hard limit - if exceeded, the message will not be delivered
- Reduce the summary to 3-5 most important points to fit within the limit

Focus on:
- Important news and announcements
- Key discussions and debates
- Decisions made or conclusions reached
- Useful resources and links

Response format:
- 3-5 informative bullet points
- Each point: 1-2 sentences (maximum 150-200 characters)
- Use emojis for categorization
- Be concise but informative
- VERIFY that the final length does NOT exceed 3500 characters

Messages (total: {len(messages)}):
---
{messages_text}
---

Respond ONLY in {self.output_language}. Remember: maximum 3500 characters!
"""

        system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{language}", self.output_language)
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            summary = await self.provider.chat_completion(
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
            summary = await self.provider.chat_completion(
                messages=chat_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=retry_max_tokens,
            )
        except Exception as e:
            self.logger.error(f"AI provider error for {channel_name}: {e}")
            raise

        self.logger.debug(f"Summary for {channel_name}: {len(summary)} chars")
        return summary

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
            text = msg.text[:500] if len(msg.text) > 500 else msg.text
            formatted.append(f"{i}. [{timestamp}] {msg.sender}: {text}")

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

        return "\n".join(reversed(selected))


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
