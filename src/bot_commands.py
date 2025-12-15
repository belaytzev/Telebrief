"""
Bot command handlers for instant digest generation.
"""

import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.config_loader import Config
from src.core import generate_and_send_channel_digests
from src.scheduler import DigestScheduler


class BotCommandHandler:
    """Handles bot commands for manual digest generation."""

    def __init__(
        self, config: Config, logger: logging.Logger, scheduler: Optional[DigestScheduler] = None
    ):
        """
        Initialize bot command handler.

        Args:
            config: Application configuration
            logger: Logger instance
            scheduler: Scheduler instance (for status command)
        """
        self.config = config
        self.logger = logger
        self.scheduler = scheduler
        self.app: Optional[Application] = None

    def setup_application(self) -> Application:
        """
        Set up Telegram bot application.

        Returns:
            Configured Application instance
        """
        # Create application
        self.app = Application.builder().token(self.config.telegram_bot_token).build()

        # Add command handlers
        self.app.add_handler(CommandHandler("digest", self.handle_digest))
        self.app.add_handler(CommandHandler("status", self.handle_status))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("start", self.handle_help))

        self.logger.info("Bot command handlers registered")
        return self.app

    def is_authorized(self, user_id: int) -> bool:
        """
        Check if user is authorized.

        Args:
            user_id: Telegram user ID

        Returns:
            True if authorized
        """
        return user_id == self.config.settings.target_user_id

    async def handle_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /digest command.

        Args:
            update: Telegram update
            context: Bot context
        """
        # Type checks for command handlers
        assert update.effective_user is not None
        assert update.message is not None

        user_id = update.effective_user.id

        # Security check
        if not self.is_authorized(user_id):
            self.logger.warning(f"Unauthorized /digest attempt from user {user_id}")
            return  # Silently ignore

        self.logger.info(f"Manual digest requested by user {user_id}")

        # Send "processing" message
        await update.message.reply_text(
            "⏳ Генерирую дайджест за последние 24 часа...\n" "Это может занять 1-2 минуты."
        )

        try:
            # Generate and send digest
            success = await generate_and_send_channel_digests(
                config=self.config, logger=self.logger, hours=24, user_id=user_id
            )

            if success:
                await update.message.reply_text(
                    "✅ Дайджест готов! Каждый канал отправлен отдельным сообщением."
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при генерации дайджеста. " "Проверьте логи для деталей."
                )

        except Exception as e:
            self.logger.error(f"Error in /digest command: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /status command.

        Args:
            update: Telegram update
            context: Bot context
        """
        # Type checks for command handlers
        assert update.effective_user is not None
        assert update.message is not None

        user_id = update.effective_user.id

        # Security check
        if not self.is_authorized(user_id):
            self.logger.warning(f"Unauthorized /status attempt from user {user_id}")
            return

        # Gather status information
        status_lines = [
            "📊 **Статус Telebrief**\n",
            f"🤖 Модель: {self.config.settings.openai_model}",
            f"📺 Каналов настроено: {len(self.config.channels)}",
        ]

        if self.scheduler:
            next_run = self.scheduler.get_next_run_time()
            status_lines.append(f"⏰ Следующий дайджест: {next_run}")
        else:
            status_lines.append("⏰ Планировщик не запущен")

        status_lines.extend(
            [
                "",
                "**Доступные команды:**",
                "/digest - Сгенерировать дайджест сейчас",
                "/status - Показать этот статус",
                "/help - Помощь",
            ]
        )

        await update.message.reply_text("\n".join(status_lines), parse_mode="Markdown")

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /help and /start commands.

        Args:
            update: Telegram update
            context: Bot context
        """
        # Type checks for command handlers
        assert update.effective_user is not None
        assert update.message is not None

        user_id = update.effective_user.id

        # Security check
        if not self.is_authorized(user_id):
            return

        help_text = """
🤖 **Telebrief - Telegram Digest Generator**

Я автоматически генерирую ежедневные дайджесты из ваших Telegram-каналов с помощью AI.

**Команды:**

/digest - Сгенерировать дайджест за последние 24 часа
/status - Показать статус и настройки
/help - Показать эту справку

**Автоматический режим:**
Дайджест генерируется автоматически каждый день в {}

**Возможности:**
• Обработка каналов на любых языках
• Вывод всегда на русском языке
• Умные суммаризации с помощью GPT-5
• Ссылки на оригинальные сообщения
        """.format(
            self.config.settings.schedule_time + " UTC"
        )

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def run(self):
        """Run the bot (polling mode)."""
        if not self.app:
            self.setup_application()

        assert self.app is not None
        assert self.app.updater is not None

        self.logger.info("Starting bot polling...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        self.logger.info("✅ Bot is running and listening for commands")

    async def stop(self):
        """Stop the bot."""
        if self.app and self.app.updater:
            self.logger.info("Stopping bot...")
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()


async def main():
    """Test bot commands."""
    from src.config_loader import load_config
    from src.utils import setup_logging

    config = load_config()
    logger = setup_logging(config.log_level)

    handler = BotCommandHandler(config, logger)
    handler.setup_application()

    logger.info("Bot command handler ready. Starting polling...")

    try:
        await handler.run()
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
        await handler.stop()


if __name__ == "__main__":
    asyncio.run(main())
