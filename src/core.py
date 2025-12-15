"""
Core digest generation function.
"""

import logging
from datetime import datetime
from typing import Optional

from src.collector import MessageCollector
from src.config_loader import Config
from src.formatter import DigestFormatter
from src.sender import DigestSender
from src.summarizer import Summarizer


async def generate_digest(config: Config, logger: logging.Logger, hours: int = 24) -> str:
    """
    Core digest generation function.
    Used by both scheduler and bot commands.

    Args:
        config: Application configuration
        logger: Logger instance
        hours: Lookback period in hours

    Returns:
        Formatted digest string

    Raises:
        Exception: If digest generation fails
    """
    start_time = datetime.utcnow()
    logger.info(f"{'=' * 60}")
    logger.info(f"Starting digest generation for last {hours} hours")
    logger.info(f"{'=' * 60}")

    try:
        # Step 1: Collect messages
        logger.info("STEP 1: Collecting messages from Telegram")
        collector = MessageCollector(config, logger)

        await collector.connect()
        try:
            messages_by_channel = await collector.fetch_messages(hours=hours)
        finally:
            await collector.disconnect()

        total_messages = sum(len(msgs) for msgs in messages_by_channel.values())
        logger.info(f"Collected {total_messages} messages from {len(messages_by_channel)} channels")

        # Step 2: Generate summaries
        logger.info("STEP 2: Generating AI summaries")
        summarizer = Summarizer(config, logger)
        summary_result = await summarizer.summarize_all(messages_by_channel)

        channel_summaries = summary_result["channel_summaries"]
        overview = summary_result["overview"]

        logger.info(f"Generated summaries for {len(channel_summaries)} channels")
        logger.debug(f"Overview length: {len(overview) if overview else 0} chars")
        logger.debug(f"Overview content: {overview[:200] if overview else 'EMPTY'}")
        for ch_name, ch_summary in channel_summaries.items():
            logger.debug(
                f"Channel '{ch_name}' summary length: {len(ch_summary) if ch_summary else 0} chars"
            )
            logger.debug(
                f"Channel '{ch_name}' summary: {ch_summary[:200] if ch_summary else 'EMPTY'}"
            )

        # Step 3: Format digest
        logger.info("STEP 3: Formatting digest")
        formatter = DigestFormatter(config, logger)
        digest = formatter.create_digest(
            overview=overview,
            channel_summaries=channel_summaries,
            messages_by_channel=messages_by_channel,
            hours=hours,
        )

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(f"{'=' * 60}")
        logger.info(f"✅ Digest generation completed in {execution_time:.1f}s")
        logger.info(f"{'=' * 60}")

        return digest

    except Exception as e:
        logger.error(f"❌ Digest generation failed: {e}", exc_info=True)
        raise


async def generate_and_send_digest(
    config: Config, logger: logging.Logger, hours: int = 24, user_id: Optional[int] = None
) -> bool:
    """
    Generate and send digest.

    Args:
        config: Application configuration
        logger: Logger instance
        hours: Lookback period
        user_id: Target user ID

    Returns:
        True if successful
    """
    try:
        # Generate digest
        digest = await generate_digest(config, logger, hours)

        # Send digest
        logger.info("STEP 4: Sending digest")
        sender = DigestSender(config, logger)
        success = await sender.send_digest(digest, user_id)

        return success

    except Exception as e:
        logger.error(f"Failed to generate and send digest: {e}")
        return False


async def generate_and_send_channel_digests(
    config: Config, logger: logging.Logger, hours: int = 24, user_id: Optional[int] = None
) -> bool:
    """
    Generate and send separate digest messages for each channel.

    Args:
        config: Application configuration
        logger: Logger instance
        hours: Lookback period
        user_id: Target user ID

    Returns:
        True if successful
    """
    start_time = datetime.utcnow()
    logger.info(f"{'=' * 60}")
    logger.info(f"Starting per-channel digest generation for last {hours} hours")
    logger.info(f"{'=' * 60}")

    try:
        # Step 1: Collect messages
        logger.info("STEP 1: Collecting messages from Telegram")
        collector = MessageCollector(config, logger)

        await collector.connect()
        try:
            messages_by_channel = await collector.fetch_messages(hours=hours)
        finally:
            await collector.disconnect()

        total_messages = sum(len(msgs) for msgs in messages_by_channel.values())
        logger.info(f"Collected {total_messages} messages from {len(messages_by_channel)} channels")

        if total_messages == 0:
            logger.warning("No messages collected, skipping digest generation")
            return False

        # Step 2: Generate summaries
        logger.info("STEP 2: Generating AI summaries")
        summarizer = Summarizer(config, logger)
        summary_result = await summarizer.summarize_all(messages_by_channel)

        channel_summaries = summary_result["channel_summaries"]
        logger.info(f"Generated summaries for {len(channel_summaries)} channels")

        # Step 3: Format individual channel messages
        logger.info("STEP 3: Formatting individual channel messages")
        formatter = DigestFormatter(config, logger)
        channel_messages = []

        for channel_name, summary in channel_summaries.items():
            # Skip empty summaries or errors
            if not summary or "ошибка" in summary.lower():
                logger.warning(f"Skipping channel '{channel_name}': empty or error summary")
                continue

            # Get messages for this channel
            messages = messages_by_channel.get(channel_name, [])

            # Format message
            formatted_message = formatter.format_channel_message(
                channel_name=channel_name, summary=summary, messages=messages, hours=hours
            )

            channel_messages.append((channel_name, formatted_message))
            logger.info(f"Formatted message for {channel_name}: {len(formatted_message)} chars")

        if not channel_messages:
            logger.warning("No valid channel messages to send")
            return False

        # Step 4: Send channel messages
        logger.info(f"STEP 4: Sending {len(channel_messages)} channel messages")
        sender = DigestSender(config, logger)
        success = await sender.send_channel_messages(channel_messages, user_id)

        # Step 5: Send summary message
        if success:
            logger.info("STEP 5: Sending summary message")
            summary_message = formatter.format_summary_message(
                total_channels=len(channel_messages), total_messages=total_messages, hours=hours
            )
            await sender.send_message(summary_message, user_id)

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(f"{'=' * 60}")
        logger.info(f"✅ Per-channel digest generation completed in {execution_time:.1f}s")
        logger.info(f"{'=' * 60}")

        return success

    except Exception as e:
        logger.error(f"❌ Per-channel digest generation failed: {e}", exc_info=True)
        return False
