"""
Telegram bot sender for delivering digests.
"""

import asyncio
import logging
from typing import Optional

from telegram import Bot, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError

from src.config_loader import Config
from src.formatter import DigestFormatter
from src.utils import (
    clear_digest_message_ids,
    get_digest_message_ids,
    save_digest_message_ids,
    split_message,
)


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
        self.bot_id = int(config.telegram_bot_token.split(":")[0])
        self.formatter = DigestFormatter(config, logger)

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

    async def send_channel_messages(
        self, channel_messages: list[tuple[str, str]], user_id: Optional[int] = None
    ) -> bool:
        """
        Send separate messages for each channel.

        Args:
            channel_messages: List of (channel_name, message_text) tuples
            user_id: Target user ID (defaults to configured user)

        Returns:
            True if all messages sent successfully, False otherwise
        """
        if user_id is None:
            user_id = self.target_user_id

        # Verify authorized user
        if user_id != self.target_user_id:
            self.logger.warning(f"Unauthorized send attempt to user {user_id}")
            return False

        self.logger.info(f"Sending {len(channel_messages)} channel messages to user {user_id}")

        success_count = 0
        failed_channels = []

        for i, (channel_name, message_text) in enumerate(channel_messages, 1):
            try:
                self.logger.info(f"Sending message {i}/{len(channel_messages)}: {channel_name}")

                # Verify message length
                if len(message_text) > 4096:
                    self.logger.error(
                        f"Message for '{channel_name}' exceeds 4096 chars ({len(message_text)}), splitting..."
                    )
                    # Split and send parts
                    parts = split_message(message_text, max_length=4000)
                    for part_num, part in enumerate(parts, 1):
                        await self._send_message_part(user_id, part, part_num)
                        self.logger.info(f"Sent part {part_num}/{len(parts)} for {channel_name}")
                else:
                    # Send as single message
                    await self._send_message_part(user_id, message_text, 1)

                success_count += 1
                self.logger.info(f"✅ Successfully sent message for {channel_name}")

                # Small delay between messages to avoid rate limiting
                if i < len(channel_messages):
                    await asyncio.sleep(0.5)

            except TelegramError as e:
                self.logger.error(f"❌ Failed to send message for {channel_name}: {e}")
                failed_channels.append(channel_name)
                continue

        # Log summary
        if success_count == len(channel_messages):
            self.logger.info(f"✅ All {success_count} channel messages sent successfully")
            return True
        else:
            self.logger.warning(
                f"⚠️ Sent {success_count}/{len(channel_messages)} messages. "
                f"Failed: {', '.join(failed_channels)}"
            )
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

    async def cleanup_old_digests(self, user_id: Optional[int] = None) -> bool:
        """
        Delete previous digest messages.

        Args:
            user_id: Target user ID (defaults to configured user)

        Returns:
            True if cleanup successful, False otherwise
        """
        if user_id is None:
            user_id = self.target_user_id

        # Verify authorized user
        if user_id != self.target_user_id:
            self.logger.warning(f"Unauthorized cleanup attempt for user {user_id}")
            return False

        # Get stored message IDs
        message_ids = get_digest_message_ids(user_id)

        if not message_ids:
            self.logger.info("No previous digest messages to clean up")
            return True

        self.logger.info(f"Cleaning up {len(message_ids)} previous digest messages")

        deleted_count = 0
        failed_count = 0

        for message_id in message_ids:
            try:
                await self.bot.delete_message(chat_id=user_id, message_id=message_id)
                deleted_count += 1
            except TelegramError as e:
                # Message might already be deleted or not found
                if "message to delete not found" in str(e).lower():
                    self.logger.debug(f"Message {message_id} already deleted")
                    deleted_count += 1
                else:
                    self.logger.warning(f"Failed to delete message {message_id}: {e}")
                    failed_count += 1

        # Clear stored message IDs
        clear_digest_message_ids(user_id)

        if failed_count == 0:
            self.logger.info(f"✅ Cleaned up {deleted_count} messages successfully")
            return True
        else:
            self.logger.warning(
                f"⚠️ Cleaned up {deleted_count} messages, {failed_count} failed to delete"
            )
            return deleted_count > 0

    async def _send_message_with_tracking(
        self, user_id: int, message_text: str, channel_name: str
    ) -> Optional[int]:
        """
        Send a message with markdown fallback and return message ID.

        Args:
            user_id: Target user ID
            message_text: Message text to send
            channel_name: Channel name for logging

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            message = await self.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
            return message.message_id
        except TelegramError as e:
            if "Can't parse entities" in str(e):
                self.logger.warning("Markdown parse error, falling back to plain text")
                message = await self.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=None,
                    disable_web_page_preview=False,
                )
                return message.message_id
            raise

    async def _send_summary_message(
        self,
        user_id: int,
        summary_message: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> Optional[int]:
        """
        Send summary message and return message ID.

        Args:
            user_id: Target user ID
            summary_message: Summary message text
            reply_markup: Optional inline keyboard to attach

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            message = await self.bot.send_message(
                chat_id=user_id,
                text=summary_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup,
            )
            self.logger.info("✅ Summary message sent")
            return message.message_id
        except TelegramError as e:
            if "Can't parse entities" in str(e):
                self.logger.warning("Markdown parse error in summary, falling back to plain text")
                message = await self.bot.send_message(
                    chat_id=user_id,
                    text=summary_message,
                    parse_mode=None,
                    reply_markup=reply_markup,
                )
                self.logger.info("✅ Summary message sent (plain text fallback)")
                return message.message_id
            self.logger.warning(f"⚠️ Failed to send summary message: {e}")
            return None

    def _log_and_return_result(
        self, success_count: int, total_count: int, failed_channels: list[str]
    ) -> bool:
        """
        Log summary and return success status.

        Args:
            success_count: Number of successful sends
            total_count: Total number of messages
            failed_channels: List of failed channel names

        Returns:
            True if all successful, False otherwise
        """
        if success_count == total_count:
            self.logger.info(f"✅ All {success_count} channel messages sent successfully")
            return True
        self.logger.warning(
            f"⚠️ Sent {success_count}/{total_count} messages. "
            f"Failed: {', '.join(failed_channels)}"
        )
        return success_count > 0

    async def _send_channel_messages_loop(
        self, user_id: int, channel_messages: list[tuple[str, str]]
    ) -> tuple[list[int], list[tuple[str, int]], int, list[str]]:
        """
        Send messages for all channels.

        Args:
            user_id: Target user ID
            channel_messages: List of (channel_name, message_text) tuples

        Returns:
            Tuple of (sent_message_ids, channel_id_map, success_count, failed_channels)
        """
        sent_message_ids = []
        channel_id_map: list[tuple[str, int]] = []
        success_count = 0
        failed_channels = []

        for i, (channel_name, message_text) in enumerate(channel_messages, 1):
            try:
                self.logger.info(f"Sending message {i}/{len(channel_messages)}: {channel_name}")

                message_id = await self._send_message_with_tracking(
                    user_id, message_text, channel_name
                )
                if message_id:
                    sent_message_ids.append(message_id)
                    channel_id_map.append((channel_name, message_id))
                    success_count += 1
                    self.logger.info(f"✅ Successfully sent message for {channel_name}")

                if i < len(channel_messages):
                    await asyncio.sleep(0.5)

            except TelegramError as e:
                self.logger.error(f"❌ Failed to send message for {channel_name}: {e}")
                failed_channels.append(channel_name)
                continue

        return sent_message_ids, channel_id_map, success_count, failed_channels

    async def _edit_summary_keyboard(
        self,
        user_id: int,
        summary_id: int,
        keyboard: Optional[InlineKeyboardMarkup],
    ) -> None:
        """
        Edit the summary message to attach the TOC inline keyboard.

        Args:
            user_id: Chat ID the summary was sent to
            summary_id: Message ID of the summary placeholder
            keyboard: Inline keyboard to attach
        """
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=summary_id,
                reply_markup=keyboard,
            )
            self.logger.info("✅ Summary TOC keyboard updated")
        except TelegramError as e:
            self.logger.warning(f"⚠️ Failed to update summary keyboard: {e}")

    async def send_channel_messages_with_tracking(
        self,
        channel_messages: list[tuple[str, str]],
        summary_message: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> bool:
        """
        Send separate messages for each channel and track message IDs for cleanup.

        Sends the summary placeholder first so it appears at the top, then sends
        each channel message, then edits the placeholder to add the TOC keyboard.

        Args:
            channel_messages: List of (channel_name, message_text) tuples
            summary_message: Optional summary message to send first as TOC header
            user_id: Target user ID (defaults to configured user)

        Returns:
            True if all messages sent successfully, False otherwise
        """
        if user_id is None:
            user_id = self.target_user_id

        if user_id != self.target_user_id:
            self.logger.warning(f"Unauthorized send attempt to user {user_id}")
            return False

        self.logger.info(f"Sending {len(channel_messages)} channel messages to user {user_id}")

        # Send summary placeholder FIRST so it appears at the top of the chat
        summary_id = None
        if summary_message:
            summary_id = await self._send_summary_message(user_id, summary_message)

        # Send all channel messages and collect their IDs
        sent_message_ids, channel_id_map, success_count, failed_channels = (
            await self._send_channel_messages_loop(user_id, channel_messages)
        )

        # Edit the placeholder to add the TOC keyboard now that channel IDs are known
        if summary_message and summary_id and success_count > 0:
            # Use bot_id so tg://openmessage?user_id=BOT_ID opens the chat with the bot
            toc_peer_id = self.bot_id if user_id > 0 else user_id
            keyboard = self.formatter.build_toc_keyboard(channel_id_map, toc_peer_id)
            await self._edit_summary_keyboard(user_id, summary_id, keyboard)

        # Save all message IDs for future cleanup (summary first for correct order)
        all_ids = ([summary_id] if summary_id else []) + sent_message_ids
        if all_ids:
            save_digest_message_ids(all_ids, user_id)
            self.logger.info(f"Saved {len(all_ids)} message IDs for cleanup")

        return self._log_and_return_result(success_count, len(channel_messages), failed_channels)


async def main():
    """Test sender."""
    from src.config_loader import load_config
    from src.utils import setup_logging

    config = load_config()
    logger = setup_logging(config.log_level)

    sender = DigestSender(config, logger)

    test_digest = """
📰Тестовый дайджест

📌Краткий обзор
Это тестовое сообщение для проверки отправки дайджеста.

💻 Test Channel
- Тестовый пункт 1
- Тестовый пункт 2

---
📈 **Статистика**: 1 канал, 10 сообщений
    """

    success = await sender.send_digest(test_digest)
    print(f"Send result: {'✅ Success' if success else '❌ Failed'}")


if __name__ == "__main__":
    asyncio.run(main())
