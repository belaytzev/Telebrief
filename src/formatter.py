"""
Markdown formatter for digest output.
"""

from datetime import datetime
from typing import Dict, List
import logging

from src.collector import Message
from src.config_loader import Config


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

    def create_digest(
        self,
        overview: str,
        channel_summaries: Dict[str, str],
        messages_by_channel: Dict[str, List[Message]],
        hours: int = 24
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

        # Build digest parts
        parts = []

        # Header
        header = self._create_header(hours)
        parts.append(header)

        # Overview section
        if overview:
            parts.append("## 🎯 Краткий обзор\n")
            parts.append(overview)
            parts.append("\n---\n")

        # Channel sections
        for channel_name, summary in channel_summaries.items():
            if not summary or "ошибка" in summary.lower():
                continue

            section = self._create_channel_section(
                channel_name,
                summary,
                messages_by_channel.get(channel_name, [])
            )
            parts.append(section)

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
        date_str = datetime.utcnow().strftime('%d %B %Y')
        # Translate month to Russian
        months_ru = {
            'January': 'января', 'February': 'февраля', 'March': 'марта',
            'April': 'апреля', 'May': 'мая', 'June': 'июня',
            'July': 'июля', 'August': 'августа', 'September': 'сентября',
            'October': 'октября', 'November': 'ноября', 'December': 'декабря'
        }
        for eng, rus in months_ru.items():
            date_str = date_str.replace(eng, rus)

        emoji = "📊" if self.use_emojis else ""

        return f"# {emoji} Ежедневный дайджест - {date_str}\n"

    def _create_channel_section(
        self,
        channel_name: str,
        summary: str,
        messages: List[Message]
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
        # Pick emoji based on channel name keywords
        emoji = self._pick_emoji(channel_name)

        section_parts = [
            f"## {emoji} {channel_name}\n",
            summary,
            "\n"
        ]

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
        if any(word in name_lower for word in ['tech', 'dev', 'code', 'программ', 'разработ']):
            return "💻"
        # Crypto/Finance
        elif any(word in name_lower for word in ['crypto', 'bitcoin', 'финанс', 'крипто']):
            return "💰"
        # News
        elif any(word in name_lower for word in ['news', 'новост']):
            return "📰"
        # Business
        elif any(word in name_lower for word in ['business', 'бизнес', 'startup']):
            return "💼"
        # Science
        elif any(word in name_lower for word in ['science', 'research', 'наук']):
            return "🔬"
        # AI/ML
        elif any(word in name_lower for word in ['ai', 'ml', 'artificial', 'ии', 'искусственн']):
            return "🤖"
        # Design
        elif any(word in name_lower for word in ['design', 'дизайн', 'ui', 'ux']):
            return "🎨"
        # Marketing
        elif any(word in name_lower for word in ['marketing', 'маркетинг', 'smm']):
            return "📈"
        # Default
        else:
            return "📺"

    def _create_statistics(
        self,
        messages_by_channel: Dict[str, List[Message]],
        hours: int
    ) -> str:
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
        start_time = end_time.replace(hour=end_time.hour - hours, minute=0, second=0)

        stats_parts = [
            "---\n",
            f"📈 **Статистика**: {active_channels} каналов, {total_messages} сообщений обработано"
        ]

        if hours == 24:
            stats_parts.append(
                f"⏱️ Дайджест за: {start_time.strftime('%d.%m %H:%M')} - "
                f"{end_time.strftime('%d.%m %H:%M')} UTC"
            )
        else:
            stats_parts.append(f"⏱️ Период: последние {hours} часов")

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
        """
    }

    messages_by_channel = {
        "TechCrunch": [],
        "Crypto News": []
    }

    digest = formatter.create_digest(
        overview=overview,
        channel_summaries=channel_summaries,
        messages_by_channel=messages_by_channel,
        hours=24
    )

    print(digest)


if __name__ == '__main__':
    main()
