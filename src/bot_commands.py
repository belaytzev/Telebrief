"""
Bot command handlers for instant digest generation.
"""

import asyncio
import logging
from typing import Optional

from telegram import BotCommand, Update
from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from src.config_loader import Config
from src.core import generate_and_send_channel_digests
from src.scheduler import DigestScheduler
from src.sender import DigestSender
from src.ui_strings import get_ui_strings


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
        self._ui = get_ui_strings(config.settings.output_language)

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
        self.app.add_handler(CommandHandler("cleanup", self.handle_cleanup))
        self.app.add_handler(CommandHandler("status", self.handle_status))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("start", self.handle_help))
        self.app.add_handler(CallbackQueryHandler(self.handle_toc_callback, pattern=r"^toc:"))

        self.logger.info("Bot command handlers registered")
        return self.app

    async def setup_bot_menu(self) -> None:
        """
        Set up bot command menu for easy command discovery.
        This creates the menu that appears when users type '/' in the chat.
        """
        if not self.app:
            self.logger.warning("Application not initialized, cannot set up bot menu")
            return

        commands = [
            BotCommand("start", self._ui["cmd_start_desc"]),
            BotCommand("digest", self._ui["cmd_digest_desc"]),
            BotCommand("cleanup", self._ui["cmd_cleanup_desc"]),
            BotCommand("status", self._ui["cmd_status_desc"]),
            BotCommand("help", self._ui["cmd_help_desc"]),
        ]

        try:
            await self.app.bot.set_my_commands(commands)
            self.logger.info("✅ Bot command menu configured successfully")
        except Exception as e:
            self.logger.error(f"Failed to set up bot menu: {e}")

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
        await update.message.reply_text(self._ui["generating_digest"])

        try:
            # Generate and send digest
            success = await generate_and_send_channel_digests(
                config=self.config, logger=self.logger, hours=24, user_id=user_id
            )

            if success:
                await update.message.reply_text(self._ui["digest_done"])
            else:
                await update.message.reply_text(self._ui["digest_error"])

        except Exception as e:
            self.logger.error(f"Error in /digest command: {e}", exc_info=True)
            await update.message.reply_text(self._ui["digest_exception"])

    async def handle_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /cleanup command.

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
            self.logger.warning(f"Unauthorized /cleanup attempt from user {user_id}")
            return  # Silently ignore

        self.logger.info(f"Manual cleanup requested by user {user_id}")

        # Send "processing" message
        await update.message.reply_text(self._ui["cleaning_up"])

        try:
            sender = DigestSender(self.config, self.logger)
            success = await sender.cleanup_old_digests(user_id)

            if success:
                await update.message.reply_text(self._ui["cleanup_done"])
            else:
                await update.message.reply_text(self._ui["cleanup_partial"])

        except Exception as e:
            self.logger.error(f"Error in /cleanup command: {e}", exc_info=True)
            await update.message.reply_text(self._ui["cleanup_error"])

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
        ai_model = self.config.settings.ai_model
        auto_cleanup_value = self._ui["enabled"] if self.config.settings.auto_cleanup_old_digests else self._ui["disabled"]
        status_lines = [
            self._ui["status_header"],
            f"{self._ui['provider_label']}: {self.config.settings.ai_provider}",
            f"{self._ui['model_label']}: {ai_model}",
            f"{self._ui['channels_configured']}: {len(self.config.channels)}",
            f"{self._ui['auto_cleanup_label']}: {auto_cleanup_value}",
        ]

        if self.scheduler:
            next_run = self.scheduler.get_next_run_time()
            status_lines.append(f"{self._ui['next_digest']}: {next_run}")
        else:
            status_lines.append(self._ui["scheduler_not_running"])

        status_lines.extend(
            [
                "",
                self._ui["available_commands"],
                "/digest - " + self._ui["cmd_digest_desc"],
                "/cleanup - " + self._ui["cmd_cleanup_desc"],
                "/status - " + self._ui["cmd_status_desc"],
                "/help - " + self._ui["cmd_help_desc"],
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

        help_text = (
            f"{self._ui['help_title']}\n\n"
            f"{self._ui['help_intro']}\n\n"
            f"{self._ui['help_commands_header']}\n\n"
            f"/digest - {self._ui['cmd_digest_desc']}\n"
            f"/cleanup - {self._ui['cmd_cleanup_desc']}\n"
            f"/status - {self._ui['cmd_status_desc']}\n"
            f"/help - {self._ui['cmd_help_desc']}\n\n"
            f"{self._ui['help_auto_mode']}\n"
            + self._ui["help_auto_desc"].format(
                schedule=self.config.settings.schedule_time + " UTC"
            )
            + f"\n\n{self._ui['help_features']}\n"
            + self._ui["help_features_list"].format(
                output_lang=self.config.settings.output_language,
                provider=self.config.settings.ai_provider,
            )
        )

        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def handle_toc_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle TOC inline button callbacks for private chats.

        Callback data format: ``toc:<user_id>:<message_id>``

        Copies the original channel message back to the private chat so the
        user can jump to it on any platform (including Telegram Desktop).
        """
        if update.callback_query is None or update.effective_user is None:
            return

        query = update.callback_query
        caller_id = update.effective_user.id

        # Security check — only the authorised user may trigger this
        if not self.is_authorized(caller_id):
            self.logger.warning(f"Unauthorized TOC callback from user {caller_id}")
            await query.answer()
            return

        try:
            parts = query.data.split(":")  # type: ignore[union-attr]
            user_id = int(parts[1])
            message_id = int(parts[2])
        except (AttributeError, IndexError, ValueError) as exc:
            self.logger.error(f"Malformed TOC callback data '{query.data}': {exc}")
            await query.answer()
            return

        # Security check — the user_id embedded in callback_data must match the caller
        if user_id != caller_id:
            self.logger.warning(f"TOC callback user_id mismatch: {user_id} vs {caller_id}")
            await query.answer()
            return

        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=user_id,
                message_id=message_id,
            )
            await query.answer()
            self.logger.debug(f"TOC callback: copied message {message_id} for user {user_id}")
        except TelegramError as exc:
            self.logger.error(f"TOC callback copy_message failed: {exc}")
            await query.answer(text=str(exc)[:200])

    async def run(self):
        """Run the bot (polling mode)."""
        if not self.app:
            self.setup_application()

        assert self.app is not None
        assert self.app.updater is not None

        self.logger.info("Starting bot polling...")
        await self.app.initialize()
        await self.app.start()

        # Set up bot command menu
        await self.setup_bot_menu()

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
