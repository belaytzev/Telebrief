"""
Core digest generation function.
"""

import logging
from datetime import datetime

from src.config_loader import Config
from src.collector import MessageCollector
from src.summarizer import Summarizer
from src.formatter import DigestFormatter
from src.sender import DigestSender


async def generate_digest(
    config: Config,
    logger: logging.Logger,
    hours: int = 24
) -> str:
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
        messages_by_channel = await collector.fetch_messages(hours=hours)
        await collector.disconnect()

        total_messages = sum(len(msgs) for msgs in messages_by_channel.values())
        logger.info(f"Collected {total_messages} messages from {len(messages_by_channel)} channels")

        # Step 2: Generate summaries
        logger.info("STEP 2: Generating AI summaries")
        summarizer = Summarizer(config, logger)
        summary_result = await summarizer.summarize_all(messages_by_channel)

        channel_summaries = summary_result['channel_summaries']
        overview = summary_result['overview']

        logger.info(f"Generated summaries for {len(channel_summaries)} channels")

        # Step 3: Format digest
        logger.info("STEP 3: Formatting digest")
        formatter = DigestFormatter(config, logger)
        digest = formatter.create_digest(
            overview=overview,
            channel_summaries=channel_summaries,
            messages_by_channel=messages_by_channel,
            hours=hours
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
    config: Config,
    logger: logging.Logger,
    hours: int = 24,
    user_id: int = None
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
