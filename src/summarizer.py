"""
AI-powered summarizer using OpenAI API with Russian output.
"""

import asyncio
import logging
from typing import Any, Dict, List

from openai import AsyncOpenAI

from src.collector import Message
from src.config_loader import Config

# Russian system prompt
SYSTEM_PROMPT = """
Ты — профессиональный ассистент по созданию новостных дайджестов для Telegram.

КРИТИЧЕСКИ ВАЖНО:
* Всегда отвечай ТОЛЬКО на русском языке, независимо от языка входных сообщений.
* Форматируй вывод под Telegram-сообщение: кратко, структурировано, с эмодзи и визуальными разделителями.
* Указывай источники только для действительно важных сообщений из Telegram-чатов; отдельный раздел «Источники» не нужен — интегрируй ссылку/упоминание прямо в соответствующий пункт.

Твоя задача:
* Анализировать входные материалы на любых языках (английский, русский, украинский, китайский и др.).
* Предоставлять сжатое, чётко структурированное резюме на русском языке для Telegram.
* Сохранять контекст, нюансы и важные детали; объединять дубли, убирать повторы.
* Отмечать расхождения между источниками и помечать неподтверждённые данные.

Формат и оформление (для Telegram):
* Используй эмодзи для акцентов и семантики (например: 📚 тема, 🆕 новое, 📊 цифры, ⚠️ риск, ✅ подтверждено, ❗важно, 🌐 ссылка).
* Разделяй блоки визуально: строки с «— — —», «•••», пустые строки.
* Максимальная читаемость с мобильного: короткие абзацы, 1–2 предложения на пункт.
* Встраивай источник только там, где это критично (важные сообщения из Telegram-чата): укажи @канал или ссылку 🔗 в конце соответствующего пункта.

Структура ответа:
* Заголовок (1–2 строки) с эмодзи, отражающий суть дайджеста.
* Что важно — 3–7 пунктов с ключевыми фактами, датами, именами, цифрами. Для каждого пункта:
    * Кратко по делу.
    * Эмодзи в начале.
    * Если критично — встроенная ссылка/упоминание источника 🔗@канал.

Правила стилевого оформления:
* Ясно, нейтрально, без жаргона и лишней эмоциональности.
* Сохраняй числовые данные и собственные имена точно; при неоднозначности — помечай «неподтверждено».
* При переводе сохраняй терминологию и интенцию автора.
* Избегай перегруза ссылками: только для важных сообщений из Telegram.

Технические ограничения:
* Объём основного резюме: 120–250 слов (кратко) или 250–500 слов (расширенно), ориентируясь на читаемость в одном-двух экранах.
* Используй визуальные разделители между секциями.
* Не добавляй отдельный список источников; ссылки/упоминания — только внутри соответствующих пунктов.

Шаблон вывода (Telegram-ready):
* 🔹 [кратко]
— — —
* ❗Что важно:
    * [эмодзи] [краткий факт, цифры, имена] [при необходимости: 🔗@канал/ссылка]
    * [эмодзи] [краткий факт] [при необходимости: 🔗@канал/ссылка]
    * [эмодзи] [краткий факт] [при необходимости: 🔗@канал/ссылка]
— — —

Если вход включает несколько материалов, сгруппируй по темам с подзаголовками и разделителями; связывай события, указывая причинно-следственные связи.
"""


class Summarizer:
    """Generates AI-powered summaries in Russian using OpenAI."""

    def __init__(self, config: Config, logger: logging.Logger):
        """
        Initialize summarizer.

        Args:
            config: Application configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.model = config.settings.openai_model
        self.temperature = config.settings.openai_temperature
        self.max_tokens = config.settings.max_tokens_per_summary

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
                self.logger.info(f"✓ Summarized {channel_name}")
            except Exception as e:
                self.logger.error(f"✗ Failed to summarize {channel_name}: {e}")
                summaries[channel_name] = f"Ошибка при обработке канала: {str(e)}"

        return summaries

    async def _summarize_channel(self, channel_name: str, messages: List[Message]) -> str:
        """
        Generate summary for a single channel.

        Args:
            channel_name: Name of the channel
            messages: List of messages

        Returns:
            Summary in Russian
        """
        # Format messages for prompt
        messages_text = self._format_messages_for_prompt(messages)

        prompt = f"""
Проанализируй следующие сообщения из Telegram-канала "{channel_name}" и создай краткое резюме на русском языке.

Сфокусируйся на:
- 📰 Важных новостях и анонсах
- 💬 Ключевых обсуждениях и дебатах
- ✅ Принятых решениях или выводах
- 🔗 Полезных ресурсах и ссылках

Формат ответа:
- 3-5 информативных пунктов (bullet points)
- Каждый пункт: 1-2 предложения
- Используй эмодзи для категоризации
- Будь лаконичен но информативен

Сообщения (всего: {len(messages)}):
---
{messages_text}
---

Ответь ТОЛЬКО на русском языке.
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )

            self.logger.debug(f"API response for {channel_name}: {response}")
            self.logger.debug(f"Response choices: {response.choices}")

            content = response.choices[0].message.content
            self.logger.debug(f"Raw content for {channel_name}: {repr(content)}")
            self.logger.debug(f"Content type: {type(content)}, is None: {content is None}")

            summary = content.strip() if content else ""
            self.logger.debug(f"Final summary for {channel_name}: {len(summary)} chars")
            return summary

        except Exception as e:
            self.logger.error(f"OpenAI API error for {channel_name}: {e}")
            raise

    def _format_messages_for_prompt(self, messages: List[Message]) -> str:
        """
        Format messages for inclusion in prompt.

        Args:
            messages: List of messages

        Returns:
            Formatted string
        """
        formatted = []

        for i, msg in enumerate(messages, 1):
            timestamp = msg.timestamp.strftime("%H:%M")
            text = msg.text[:500] if len(msg.text) > 500 else msg.text  # Truncate long messages
            formatted.append(f"{i}. [{timestamp}] {msg.sender}: {text}")

        return "\n".join(formatted)


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
