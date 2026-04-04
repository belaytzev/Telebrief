"""
Core digest generation function.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from src.collector import MessageCollector
from src.config_loader import Config
from src.formatter import DigestFormatter
from src.grouper import DigestGrouper
from src.sender import DigestSender
from src.summarizer import ERROR_SUMMARY_PREFIX, Summarizer

_CHANNEL_URL_RE = re.compile(r"^https://t\.me/(?:c/\d+|[^/]{2,})$")


async def _collect_messages(config: Config, logger: logging.Logger, hours: int) -> dict:
    """Collect messages from Telegram channels."""
    logger.info("Collecting messages from Telegram")
    collector = MessageCollector(config, logger)
    await collector.connect()
    try:
        messages_by_channel = await collector.fetch_messages(hours=hours)
    finally:
        await collector.disconnect()
    total = sum(len(msgs) for msgs in messages_by_channel.values())
    logger.info(f"Collected {total} messages from {len(messages_by_channel)} channels")
    return messages_by_channel


async def _summarize_channels(
    config: Config, logger: logging.Logger, messages_by_channel: dict
) -> dict:
    """Generate AI summaries for all channels."""
    logger.info("Generating AI summaries")
    summarizer = Summarizer(config, logger)
    summary_result = await summarizer.summarize_all(messages_by_channel)
    logger.info(f"Generated summaries for {len(summary_result['channel_summaries'])} channels")
    return summary_result


def _filter_valid_summaries(channel_summaries: dict) -> dict:
    """Filter out empty or error summaries."""
    return {
        name: summary
        for name, summary in channel_summaries.items()
        if summary and not summary.lower().startswith(ERROR_SUMMARY_PREFIX.lower())
    }


def _build_channel_urls(messages_by_channel: dict) -> dict[str, str]:
    """Extract base channel URL for each channel from its messages."""
    urls: dict[str, str] = {}
    for channel_name, messages in messages_by_channel.items():
        for msg in messages:
            if msg.link and msg.link != "#":
                base = msg.link.rsplit("/", 1)[0]
                if _CHANNEL_URL_RE.match(base):
                    urls[channel_name] = base
                    break
    return urls


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
    if hours <= 0:
        raise ValueError(f"hours must be positive, got {hours}")

    start_time = datetime.now(timezone.utc)
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
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

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


async def generate_and_send_digest_grouped(
    config: Config, logger: logging.Logger, hours: int = 24, user_id: Optional[int] = None
) -> bool:
    """
    Generate and send digest messages grouped by topic.

    Collects messages, summarizes per channel, then uses AI to classify
    bullet points into user-defined topic groups. Each group is sent as
    a separate Telegram message.

    Args:
        config: Application configuration
        logger: Logger instance
        hours: Lookback period
        user_id: Target user ID

    Returns:
        True if successful
    """
    if hours <= 0:
        raise ValueError(f"hours must be positive, got {hours}")

    try:
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting digest-grouped generation for last {hours} hours")

        messages_by_channel = await _collect_messages(config, logger, hours)
        if not sum(len(msgs) for msgs in messages_by_channel.values()):
            logger.warning("No messages collected, skipping digest generation")
            return False

        summary_result = await _summarize_channels(config, logger, messages_by_channel)
        valid_summaries = _filter_valid_summaries(summary_result["channel_summaries"])
        if not valid_summaries:
            logger.warning("No valid channel summaries to group")
            return False

        logger.info("Grouping summaries by topic")
        channel_urls = _build_channel_urls(messages_by_channel)
        grouper = DigestGrouper(config, logger)
        grouped = await grouper.group_summaries(valid_summaries, channel_urls)
        if not grouped:
            logger.warning("No groups produced, skipping send")
            return False

        logger.info("Formatting group messages")
        formatter = DigestFormatter(config, logger)
        group_messages = [
            (name, fmt)
            for name, points in grouped.items()
            if points
            for fmt in [formatter.format_group_message(group_name=name, points=points, hours=hours)]
            if fmt
        ]
        if not group_messages:
            logger.warning("No valid group messages to send")
            return False

        sender = DigestSender(config, logger)
        if config.settings.auto_cleanup_old_digests:
            await sender.cleanup_old_digests(user_id)

        total_points = sum(len(pts) for pts in grouped.values())
        group_names = [name for name, _ in group_messages]
        summary_message = formatter.format_group_summary_message(
            group_names=group_names, total_points=total_points, hours=hours
        )
        success = await sender.send_channel_messages_with_tracking(
            group_messages, summary_message, user_id
        )

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Digest-grouped generation completed in {execution_time:.1f}s")
        return success

    except Exception as e:
        logger.error(f"Digest-grouped generation failed: {e}", exc_info=True)
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
    # Mode switch: delegate to grouped flow if digest mode is "digest"
    if config.settings.digest_mode == "digest":
        return await generate_and_send_digest_grouped(config, logger, hours, user_id)

    if hours <= 0:
        raise ValueError(f"hours must be positive, got {hours}")

    start_time = datetime.now(timezone.utc)
    logger.info(f"Starting per-channel digest generation for last {hours} hours")

    try:
        messages_by_channel = await _collect_messages(config, logger, hours)
        total_messages = sum(len(msgs) for msgs in messages_by_channel.values())
        if total_messages == 0:
            logger.warning("No messages collected, skipping digest generation")
            return False

        summary_result = await _summarize_channels(config, logger, messages_by_channel)
        channel_summaries = summary_result["channel_summaries"]
        valid_summaries = _filter_valid_summaries(channel_summaries)

        formatter = DigestFormatter(config, logger)
        channel_messages = []
        for channel_name, summary in valid_summaries.items():
            messages = messages_by_channel.get(channel_name, [])
            formatted_message = formatter.format_channel_message(
                channel_name=channel_name, summary=summary, messages=messages, hours=hours
            )
            channel_messages.append((channel_name, formatted_message))

        if not channel_messages:
            logger.warning("No valid channel messages to send")
            return False

        sender = DigestSender(config, logger)
        if config.settings.auto_cleanup_old_digests:
            await sender.cleanup_old_digests(user_id)

        summary_message = formatter.format_summary_message(
            total_channels=len(channel_messages), total_messages=total_messages, hours=hours
        )
        success = await sender.send_channel_messages_with_tracking(
            channel_messages, summary_message, user_id
        )

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Per-channel digest generation completed in {execution_time:.1f}s")
        return success

    except Exception as e:
        logger.error(f"Per-channel digest generation failed: {e}", exc_info=True)
        return False
