"""
Core digest generation function.
"""

import asyncio
import inspect
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.collector import MessageCollector
from src.config_loader import ChannelConfig, Config
from src.extensions.loader import load_class
from src.formatter import DigestFormatter
from src.grouper import DigestGrouper
from src.sender import DigestSender
from src.storage import create_storage
from src.summarizer import ERROR_SUMMARY_PREFIX, Summarizer
from src.ui_strings import get_ui_strings
from src.utils import split_message

_CHANNEL_URL_RE = re.compile(r"^https://t\.me/(?:c/\d+|[^/]{2,})$")

_DIGEST_CACHE_PATH = Path("data/last_digest.json")
MAX_DIGEST_HOURS = 168  # one week; guards against a caller asking for a year of history

# ponytail: one process-wide lock, not per-source; the scheduler, the bot and the
# MCP server all build digests, and concurrent runs fight over the single
# Telethon session file. Per-channel locking only if generation becomes a bottleneck.
_digest_lock = asyncio.Lock()


async def _save_to_storage(
    config: Config, messages_by_channel: dict, logger: logging.Logger
) -> None:
    """Persist collected messages to the configured storage backend, if enabled."""
    sc = config.storage
    storage = None
    try:
        storage = await create_storage(sc)
    except Exception as e:
        logger.error(
            f"Storage init failed ({type(e).__name__}), digest continues",
            exc_info=True,
        )
    if storage:
        try:
            flat = [msg for msgs in messages_by_channel.values() for msg in msgs]
            saved = await storage.save_messages(flat)
            logger.info(f"Stored {saved} messages ({sc.backend})")
        except Exception as e:
            logger.error(
                f"Storage write failed ({type(e).__name__}), digest continues",
                exc_info=True,
            )
        finally:
            try:
                await storage.close()
            except Exception as e:
                logger.error(
                    f"Storage close failed ({type(e).__name__})",
                    exc_info=True,
                )


async def _apply_filters(
    channel_cfg: ChannelConfig,
    messages: list,
    config: Config,
    logger: logging.Logger,
) -> list:
    """Apply the effective filter chain to messages for a given channel."""
    effective_specs = (
        channel_cfg.filters if channel_cfg.filters is not None else config.settings.filters
    )
    if not effective_specs:
        return messages

    for spec in effective_specs:
        try:
            cls = load_class(spec.class_path)
            filt = cls(**spec.config)
        except Exception as e:
            logger.error(
                f"Filter load/init failed ({spec.class_path}, {type(e).__name__}), skipping",
                exc_info=True,
            )
            continue
        if not hasattr(filt, "filter"):
            logger.error(
                f"Filter {spec.class_path!r} missing filter() method, skipping",
            )
            continue
        if not inspect.iscoroutinefunction(filt.filter):
            logger.error(
                f"Filter {spec.class_path!r} filter() is not async — add 'async' keyword, skipping",
            )
            continue
        try:
            result = await filt.filter(channel_cfg, messages)
            if not isinstance(result, list):
                logger.error(
                    f"Filter {getattr(filt, 'name', spec.class_path)!r} filter() returned"
                    f" {type(result).__name__} (expected list), skipping",
                )
            else:
                messages = result
        except Exception as e:
            logger.error(
                f"Filter {getattr(filt, 'name', spec.class_path)!r} filter() raised"
                f" {type(e).__name__} ({spec.class_path}), skipping",
                exc_info=True,
            )

    return messages


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

    channel_map = {ch.name: ch for ch in config.channels}
    filtered: dict = {}
    for channel_name, msgs in messages_by_channel.items():
        ch_cfg = channel_map.get(channel_name)
        if ch_cfg is not None:
            msgs = await _apply_filters(ch_cfg, msgs, config, logger)
        else:
            logger.warning(f"Channel {channel_name!r} not in config; skipping filters")
        filtered[channel_name] = msgs
    messages_by_channel = filtered

    await _save_to_storage(config, messages_by_channel, logger)
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


def _format_group_messages(
    formatter: "DigestFormatter", grouped: dict, config: "Config", hours: int
) -> list[tuple[str, str]]:
    """Format each group into a message, ordered by config definition."""
    result = []
    for name in _order_groups(grouped, config):
        points = grouped.get(name, [])
        if not points:
            continue
        fmt = formatter.format_group_message(group_name=name, points=points, hours=hours)
        if fmt:
            for part in split_message(fmt, max_length=4000):
                result.append((name, part))
    return result


def _order_groups(grouped: dict, config: "Config") -> list[str]:
    """Order group names: config-defined order first, then remaining, 'Other' last.

    Recognizes both the localized UI string and the literal "Other"
    (case-insensitive) as the special bucket to push to the end.
    """
    config_order = [g.name for g in config.settings.digest_groups]
    localized_other = get_ui_strings(config.settings.output_language).get("group_other", "Other")

    def _is_other(name: str) -> bool:
        return name == localized_other or name.lower() == "other"

    not_config_ordered = grouped.keys() - set(config_order)
    remaining = sorted(k for k in not_config_ordered if not _is_other(k))
    other_keys = sorted(k for k in not_config_ordered if _is_other(k))
    return [n for n in config_order if n in grouped] + remaining + other_keys


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


def validate_hours(hours: int) -> None:
    """Reject lookback windows that are not a sane number of hours.

    Raises:
        ValueError: If hours is not an int in [1, MAX_DIGEST_HOURS]
    """
    if not isinstance(hours, int) or isinstance(hours, bool):
        raise ValueError(f"hours must be an int, got {hours!r}")
    if hours <= 0 or hours > MAX_DIGEST_HOURS:
        raise ValueError(f"hours must be between 1 and {MAX_DIGEST_HOURS}, got {hours}")


def _join_parts(parts: list[tuple[str, str]], summary_message: str) -> str:
    """Join digest messages into one document, header first (matches send order)."""
    return "\n\n".join([summary_message, *(text for _, text in parts)])


def _write_last_digest(text: str, hours: int, logger: logging.Logger) -> None:
    """Cache the digest so it can be served later without regenerating it.

    Written here rather than at the call sites so that scheduled digests land in
    the cache too — otherwise the cache would only ever hold on-demand runs.
    """
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hours": hours,
        "text": text,
    }
    try:
        _DIGEST_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # write-then-replace so a concurrent reader never sees a half-written file
        tmp_path = _DIGEST_CACHE_PATH.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(_DIGEST_CACHE_PATH)
    except OSError as e:
        logger.error(f"Caching digest failed ({type(e).__name__}), digest continues")


def read_last_digest() -> Optional[dict]:
    """Return the cached digest payload, or None if absent or unreadable."""
    try:
        data = json.loads(_DIGEST_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("text"), str) else None


async def _build_grouped_parts(
    config: Config, logger: logging.Logger, hours: int
) -> Optional[tuple[list[tuple[str, str]], str]]:
    """Build topic-grouped digest messages. Returns None if there is nothing to send."""
    messages_by_channel = await _collect_messages(config, logger, hours)
    if not sum(len(msgs) for msgs in messages_by_channel.values()):
        logger.warning("No messages collected, skipping digest generation")
        return None

    summary_result = await _summarize_channels(config, logger, messages_by_channel)
    valid_summaries = _filter_valid_summaries(summary_result["channel_summaries"])
    if not valid_summaries:
        logger.warning("No valid channel summaries to group")
        return None

    logger.info("Grouping summaries by topic")
    channel_urls = _build_channel_urls(messages_by_channel)
    grouper = DigestGrouper(config, logger)
    grouped = await grouper.group_summaries(valid_summaries, channel_urls)
    if not grouped:
        logger.warning("No groups produced, skipping send")
        return None

    logger.info("Formatting group messages")
    formatter = DigestFormatter(config, logger)
    group_messages = _format_group_messages(formatter, grouped, config, hours)
    if not group_messages:
        logger.warning("No valid group messages to send")
        return None

    total_points = sum(len(pts) for pts in grouped.values())
    # Same group can appear in multiple chunks when its formatted message
    # exceeds split_message threshold; dedupe while preserving order so the
    # summary header lists each group exactly once.
    group_names = list(dict.fromkeys(name for name, _ in group_messages))
    summary_message = formatter.format_group_summary_message(
        group_names=group_names, total_points=total_points, hours=hours
    )
    return group_messages, summary_message


async def _build_channel_parts(
    config: Config, logger: logging.Logger, hours: int
) -> Optional[tuple[list[tuple[str, str]], str]]:
    """Build one digest message per channel. Returns None if there is nothing to send."""
    messages_by_channel = await _collect_messages(config, logger, hours)
    total_messages = sum(len(msgs) for msgs in messages_by_channel.values())
    if total_messages == 0:
        logger.warning("No messages collected, skipping digest generation")
        return None

    summary_result = await _summarize_channels(config, logger, messages_by_channel)
    valid_summaries = _filter_valid_summaries(summary_result["channel_summaries"])

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
        return None

    summary_message = formatter.format_summary_message(
        total_channels=len(channel_messages), total_messages=total_messages, hours=hours
    )
    return channel_messages, summary_message


async def _build_digest_parts(
    config: Config, logger: logging.Logger, hours: int
) -> Optional[tuple[list[tuple[str, str]], str]]:
    """Collect, summarize and format the digest according to the configured digest_mode.

    Single chokepoint for every digest producer (scheduler, bot, MCP server), so the
    lock and the cache write only need to exist here.

    Returns:
        (messages, summary_header) or None when there is nothing worth sending
    """
    validate_hours(hours)
    async with _digest_lock:
        mode = config.settings.digest_mode
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting {mode!r} digest build for last {hours} hours")

        if mode == "digest":
            built = await _build_grouped_parts(config, logger, hours)
        else:
            built = await _build_channel_parts(config, logger, hours)

        if built is None:
            return None

        parts, summary_message = built
        _write_last_digest(_join_parts(parts, summary_message), hours, logger)

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Digest build completed in {execution_time:.1f}s")
        return parts, summary_message


async def build_digest(config: Config, logger: logging.Logger, hours: int = 24) -> str:
    """Build the digest as a single Markdown document without sending it.

    Returns:
        The digest text, or an empty string when there was nothing to report
    """
    built = await _build_digest_parts(config, logger, hours)
    return "" if built is None else _join_parts(*built)


async def generate_and_send_digest(
    config: Config, logger: logging.Logger, hours: int = 24, user_id: Optional[int] = None
) -> bool:
    """
    Build the digest according to the configured digest_mode and send it to Telegram.

    Args:
        config: Application configuration
        logger: Logger instance
        hours: Lookback period
        user_id: Target user ID

    Returns:
        True if successful

    Raises:
        ValueError: If hours is outside [1, MAX_DIGEST_HOURS]
    """
    validate_hours(hours)

    try:
        built = await _build_digest_parts(config, logger, hours)
        if built is None:
            return False
        parts, summary_message = built

        sender = DigestSender(config, logger)
        if config.settings.auto_cleanup_old_digests:
            await sender.cleanup_old_digests(user_id)

        return await sender.send_channel_messages_with_tracking(parts, summary_message, user_id)

    except Exception as e:
        logger.error(f"Digest generation failed: {e}", exc_info=True)
        return False
