"""
Markdown formatter for digest output.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.collector import Message
from src.config_loader import Config
from src.summarizer import ERROR_SUMMARY_PREFIX
from src.ui_strings import get_month_names, get_ui_strings

_CHANNEL_URL_RE = re.compile(r"^https://t\.me/(?:c/\d+|[^/]{2,})$")


class DigestFormatter:
    """Formats digest into Markdown with emojis and links."""

    def __init__(self, config: Config, logger: logging.Logger):
        """
        Initialize formatter.

        Args:
            config: Application configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.use_emojis = config.settings.use_emojis
        self.include_stats = config.settings.include_statistics
        self._language = config.settings.output_language
        self._ui = get_ui_strings(self._language)
        self._month_names = get_month_names(self._language)

    def _format_date(self, dt: datetime) -> str:
        """Return date string with month name translated to output_language.

        Uses the month index rather than strftime %B to avoid depending on the
        host system's locale setting.
        """
        month_name = self._month_names[dt.month - 1]
        return f"{dt.day:02d} {month_name} {dt.year}"

    def create_digest(
        self,
        overview: str,
        channel_summaries: Dict[str, str],
        messages_by_channel: Dict[str, List[Message]],
        hours: int = 24,
    ) -> str:
        """
        Create formatted digest.

        Args:
            overview: Executive summary
            channel_summaries: Per-channel summaries
            messages_by_channel: Original messages (for links)
            hours: Time range covered

        Returns:
            Formatted Markdown digest
        """
        self.logger.info("Formatting digest")
        self.logger.debug(
            f"Overview: {len(overview) if overview else 0} chars, truthy: {bool(overview)}"
        )
        self.logger.debug(f"Channel summaries: {len(channel_summaries)} channels")

        # Build digest parts
        parts = []

        # Header
        header = self._create_header(hours)
        parts.append(header)

        # Overview section
        if overview:
            self.logger.debug("Adding overview section")
            parts.append(f"## 🎯 {self._ui['overview']}\n")
            parts.append(overview)
            parts.append("\n---\n")
        else:
            self.logger.warning("Overview is empty or None, skipping")

        # Channel sections
        for channel_name, summary in channel_summaries.items():
            self.logger.debug(
                f"Processing channel '{channel_name}': {len(summary) if summary else 0} chars"
            )
            if not summary or summary.lower().startswith(ERROR_SUMMARY_PREFIX.lower()):
                self.logger.warning(f"Skipping channel '{channel_name}': empty or contains error")
                continue

            section = self._create_channel_section(
                channel_name, summary, messages_by_channel.get(channel_name, [])
            )
            parts.append(section)
            self.logger.debug(f"Added channel section for '{channel_name}'")

        # Statistics footer
        if self.include_stats:
            stats = self._create_statistics(messages_by_channel, hours)
            parts.append(stats)

        digest = "\n".join(parts)

        self.logger.info(f"Digest formatted: {len(digest)} characters")
        return digest

    def _create_header(self, hours: int) -> str:
        """
        Create digest header.

        Args:
            hours: Time range

        Returns:
            Header string
        """
        date_str = self._format_date(datetime.utcnow())
        emoji = "📊" if self.use_emojis else ""
        return f"# {emoji} {self._ui['daily_digest']} - {date_str}\n"

    def _extract_channel_url(self, messages: List[Message]) -> Optional[str]:
        """
        Derive the channel base URL from the first message with a valid link.

        Args:
            messages: Messages from the channel

        Returns:
            Channel URL (e.g. https://t.me/username) or None if unavailable
        """
        for msg in messages:
            if msg.link and msg.link != "#":
                base = msg.link.rsplit("/", 1)[0]
                if _CHANNEL_URL_RE.match(base):
                    return base
        return None

    def _create_channel_section(
        self, channel_name: str, summary: str, messages: List[Message]
    ) -> str:
        """
        Create section for a single channel.

        Args:
            channel_name: Channel name
            summary: Channel summary
            messages: Messages from channel (for link extraction)

        Returns:
            Formatted section
        """
        emoji = self._pick_emoji(channel_name)
        channel_url = self._extract_channel_url(messages)

        if channel_url:
            header = f"## {emoji} {channel_name} · [{self._ui['open_channel']} →]({channel_url})\n"
        else:
            header = f"## {emoji} {channel_name}\n"

        section_parts = [header, summary, "\n"]

        return "\n".join(section_parts)

    def _pick_emoji(self, channel_name: str) -> str:
        """
        Pick appropriate emoji for channel.

        Args:
            channel_name: Channel name

        Returns:
            Emoji character
        """
        if not self.use_emojis:
            return "•"

        name_lower = channel_name.lower()

        # Tech/Dev
        if any(word in name_lower for word in ["tech", "dev", "code", "программ", "разработ"]):
            return "💻"
        # Crypto/Finance
        elif any(word in name_lower for word in ["crypto", "bitcoin", "финанс", "крипто"]):
            return "💰"
        # News
        elif any(word in name_lower for word in ["news", "новост"]):
            return "📰"
        # Business
        elif any(word in name_lower for word in ["business", "бизнес", "startup"]):
            return "💼"
        # Science
        elif any(word in name_lower for word in ["science", "research", "наук"]):
            return "🔬"
        # AI/ML
        elif any(word in name_lower for word in ["ai", "ml", "artificial", "ии", "искусственн"]):
            return "🤖"
        # Design
        elif any(word in name_lower for word in ["design", "дизайн", "ui", "ux"]):
            return "🎨"
        # Marketing
        elif any(word in name_lower for word in ["marketing", "маркетинг", "smm"]):
            return "📈"
        # Default
        else:
            return "📺"

    def format_channel_message(
        self, channel_name: str, summary: str, messages: List[Message], hours: int = 24
    ) -> str:
        """
        Format a single channel's summary as a standalone Telegram message.

        Args:
            channel_name: Name of the channel
            summary: AI-generated summary
            messages: Original messages from the channel
            hours: Time range covered

        Returns:
            Formatted message ready to send
        """
        self.logger.info(f"Formatting message for channel: {channel_name}")

        parts = []

        # Channel header with date
        date_str = self._format_date(datetime.utcnow())
        emoji = self._pick_emoji(channel_name)
        channel_url = self._extract_channel_url(messages)
        if channel_url:
            header = f"# {emoji} {channel_name} · [{self._ui['open_channel']} →]({channel_url})\n*{date_str}*\n"
        else:
            header = f"# {emoji} {channel_name}\n*{date_str}*\n"
        parts.append(header)

        # Summary
        parts.append(summary)

        # Statistics for this channel
        if self.include_stats:
            message_count = len(messages)
            parts.append(f"\n---\n📊 {self._ui['messages_count']}: {message_count}")
            if hours == 24:
                parts.append(f"⏱️ {self._ui['last_hours'].format(hours=hours)}")

        message = "\n".join(parts)

        # Verify length doesn't exceed Telegram limit
        if len(message) > 4096:
            self.logger.warning(
                f"Channel message for '{channel_name}' exceeds 4096 chars ({len(message)}), truncating..."
            )
            # Truncate to 4000 to leave room for ellipsis
            message = message[:4000] + f"\n\n{self._ui['truncated']}"

        self.logger.info(f"Formatted message for {channel_name}: {len(message)} characters")
        return message

    def format_summary_message(
        self, total_channels: int, total_messages: int, hours: int = 24
    ) -> str:
        """
        Format a summary message for the digest header.

        Args:
            total_channels: Number of channels processed
            total_messages: Total messages processed
            hours: Time range covered

        Returns:
            Summary message
        """
        date_str = self._format_date(datetime.utcnow())
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        message = (
            f"📊 **{self._ui['digest_completed']}** - {date_str}\n\n"
            f"✅ {self._ui['channels_processed']}: {total_channels}\n"
            f"📨 {self._ui['total_messages']}: {total_messages}\n"
            f"⏱️ {self._ui['period']}: "
            f"{start_time.strftime('%d.%m %H:%M')} - {end_time.strftime('%d.%m %H:%M')} UTC\n"
        )
        return message

    def _create_statistics(self, messages_by_channel: Dict[str, List[Message]], hours: int) -> str:
        """
        Create statistics footer.

        Args:
            messages_by_channel: Messages grouped by channel
            hours: Time range

        Returns:
            Statistics string
        """
        total_messages = sum(len(msgs) for msgs in messages_by_channel.values())
        active_channels = sum(1 for msgs in messages_by_channel.values() if msgs)

        # Time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        stats_parts = [
            "---\n",
            f"📈 **{self._ui['stats_header']}**: {active_channels} {self._ui['channels']}, "
            f"{total_messages} {self._ui['messages_processed']}",
        ]

        if hours == 24:
            stats_parts.append(
                f"⏱️ {self._ui['digest_for']}: {start_time.strftime('%d.%m %H:%M')} - "
                f"{end_time.strftime('%d.%m %H:%M')} UTC"
            )
        else:
            stats_parts.append(f"⏱️ {self._ui['period_last_hours'].format(hours=hours)}")

        return "\n".join(stats_parts)


def main():
    """Test formatter."""
    from src.config_loader import load_config
    from src.utils import setup_logging

    config = load_config()
    logger = setup_logging(config.log_level)

    formatter = DigestFormatter(config, logger)

    # Test data
    overview = """
    Сегодня основные темы: запуск новой версии Python 3.13 обсуждался
    в нескольких технических каналах, криптовалютный рынок показал высокую
    волатильность на фоне новостей о регулировании.
    """

    channel_summaries = {
        "TechCrunch": """
- 🚀 Python 3.13 официально выпущен с улучшенной производительностью
- 🤖 OpenAI анонсировала GPT-5
- 📱 Apple vs EU: новые требования по interoperability
        """,
        "Crypto News": """
- 📈 Bitcoin волатильность: цена колебалась между $43K и $46K
- ⚠️ SEC предупреждение о новой схеме мошенничества
- 🔐 Ethereum upgrade успешно завершен
        """,
    }

    messages_by_channel: dict[str, list] = {"TechCrunch": [], "Crypto News": []}

    digest = formatter.create_digest(
        overview=overview,
        channel_summaries=channel_summaries,
        messages_by_channel=messages_by_channel,
        hours=24,
    )

    print(digest)


if __name__ == "__main__":
    main()
