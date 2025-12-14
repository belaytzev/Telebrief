"""
Telegram bot sender for delivering digests.
"""

import logging
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from src.config_loader import Config
from src.utils import split_message


class DigestSender:
    """Sends digests via Telegram bot."""

    def __init__(self, config: Config, logger: logging.Logger):
        """
        Initialize sender.

        Args:
            config: Application configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.bot = Bot(token=config.telegram_bot_token)
        self.target_user_id = config.settings.target_user_id

    async def _send_message_part(self, user_id: int, text: str, part_num: int) -> None:
        """
        Send a single message part with markdown fallback.

        Args:
            user_id: Target user ID
            text: Message text
            part_num: Part number for logging

        Raises:
            TelegramError: If sending fails (not markdown parsing)
        """
        try:
            # Try with Markdown first
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
        except TelegramError as e:
            # If markdown parsing fails, try plain text
            if "Can't parse entities" in str(e):
                self.logger.warning(
                    f"Markdown parse error in part {part_num}, falling back to plain text"
                )
                await self.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=None,
                    disable_web_page_preview=False,
                )
            else:
                raise

    async def send_digest(self, digest: str, user_id: Optional[int] = None) -> bool:
        """
        Send digest to user.

        Args:
            digest: Formatted digest text
            user_id: Target user ID (defaults to configured user)

        Returns:
            True if successful, False otherwise
        """
        if user_id is None:
            user_id = self.target_user_id

        # Verify authorized user
        if user_id != self.target_user_id:
            self.logger.warning(f"Unauthorized send attempt to user {user_id}")
            return False

        self.logger.info(f"Sending digest to user {user_id}")

        try:
            # Split message if too long
            parts = split_message(digest, max_length=4000)

            if len(parts) > 1:
                self.logger.info(f"Digest split into {len(parts)} messages")

            # Send each part
            for i, part in enumerate(parts, 1):
                await self._send_message_part(user_id, part, i)

                if len(parts) > 1:
                    self.logger.info(f"Sent part {i}/{len(parts)}")

            self.logger.info("✅ Digest sent successfully")
            return True

        except TelegramError as e:
            self.logger.error(f"❌ Failed to send digest: {e}")
            return False

    async def send_message(self, text: str, user_id: Optional[int] = None) -> bool:
        """
        Send a simple text message.

        Args:
            text: Message text
            user_id: Target user ID

        Returns:
            True if successful
        """
        if user_id is None:
            user_id = self.target_user_id

        if user_id != self.target_user_id:
            return False

        try:
            await self.bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.MARKDOWN)
            return True
        except TelegramError as e:
            self.logger.error(f"Failed to send message: {e}")
            return False


async def main():
    """Test sender."""
    from src.config_loader import load_config
    from src.utils import setup_logging

    config = load_config()
    logger = setup_logging(config.log_level)

    sender = DigestSender(config, logger)

    test_digest = """
# 📊 Тестовый дайджест

## 🎯 Краткий обзор
Это тестовое сообщение для проверки отправки дайджеста.

## 💻 Test Channel
- Тестовый пункт 1
- Тестовый пункт 2

---
📈 **Статистика**: 1 канал, 10 сообщений
    """

    success = await sender.send_digest(test_digest)
    print(f"Send result: {'✅ Success' if success else '❌ Failed'}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
