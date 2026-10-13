"""
Utility functions and logging setup for Telebrief.
"""

import html
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

# Link text may hold one level of nested brackets, e.g. a channel named "Acme [beta]".
_INLINE_MD = re.compile(
    r"`(?P<code>[^`\n]+)`"
    r"|\[(?P<ltext>(?:[^\[\]\n]|\[[^\[\]\n]*\])+)\]\((?P<url>https?://[^\s)]+)\)"
    r"|\*\*(?P<b2>[^*\s](?:[^*\n]*[^*\s])?)\*\*"
    r"|\*(?P<b1>[^*\s](?:[^*\n]*[^*\s])?)\*"
)
_HEADER_MD = re.compile(r"#{1,6}\s+(.*)")


def _inline_to_html(text: str) -> str:
    out, pos = [], 0
    for m in _INLINE_MD.finditer(text):
        out.append(html.escape(text[pos : m.start()], quote=False))
        if m["code"]:
            out.append(f"<code>{html.escape(m['code'], quote=False)}</code>")
        elif m["url"]:
            out.append(f'<a href="{html.escape(m["url"])}">{_inline_to_html(m["ltext"])}</a>')
        else:
            out.append(f"<b>{_inline_to_html(m['b2'] or m['b1'])}</b>")
        pos = m.end()
    out.append(html.escape(text[pos:], quote=False))
    return "".join(out)


def markdown_to_telegram_html(text: str) -> str:
    """Escape text for Telegram HTML, turning only bold, links, `code` and #-headers into tags."""
    lines = []
    for line in text.split("\n"):
        header = _HEADER_MD.match(line)
        lines.append(f"<b>{_inline_to_html(header[1])}</b>" if header else _inline_to_html(line))
    return "\n".join(lines)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Configure logging format
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create logger
    logger = logging.getLogger("telebrief")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # httpx logs every request URL at INFO, and Bot API URLs carry the bot token
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file = "logs/telebrief.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def get_lookback_time(hours: int) -> datetime:
    """
    Calculate lookback datetime.

    Args:
        hours: Number of hours to look back

    Returns:
        Datetime object
    """
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def split_message(text: str, max_length: int = 4000) -> list[str]:
    """
    Split long message into multiple parts for Telegram.

    Args:
        text: Text to split
        max_length: Maximum length per message

    Returns:
        List of message parts
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    for line in text.split("\n"):
        # Handle very long lines that exceed max_length
        if len(line) > max_length:
            # Save current part if it exists
            if current_part:
                parts.append(current_part.strip())
                current_part = ""

            # Split the long line into chunks
            while len(line) > max_length:
                parts.append(line[:max_length])
                line = line[max_length:]

            # Add remaining part of line to current_part
            if line:
                current_part = line + "\n"
        elif len(current_part) + len(line) + 1 <= max_length:
            current_part += line + "\n"
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = line + "\n"

    if current_part:
        parts.append(current_part.strip())

    return parts


# Message ID storage for cleanup functionality
MESSAGE_STORAGE_FILE = "data/digest_messages.json"

# How many times a single message may fail to delete before it is considered
# permanently undeletable and dropped from the retry set.
MAX_DIGEST_DELETE_ATTEMPTS = 3


def _load_digest_storage() -> dict:
    """Load the raw digest-message storage, tolerating a missing or corrupt file."""
    storage_path = Path(MESSAGE_STORAGE_FILE)
    if not storage_path.exists():
        return {}
    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_digest_storage(data: dict) -> None:
    """Persist the raw digest-message storage, creating the parent directory if needed."""
    storage_path = Path(MESSAGE_STORAGE_FILE)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storage_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_user_entry(data: dict, user_id: int) -> dict:
    """Return a user's storage entry, normalized to a dict with the expected keys."""
    entry = data.get(str(user_id))
    if not isinstance(entry, dict):
        entry = {}
    if not isinstance(entry.get("message_ids"), list):
        entry["message_ids"] = []
    if not isinstance(entry.get("delete_attempts"), dict):
        entry["delete_attempts"] = {}
    return entry


def save_digest_message_ids(message_ids: List[int], user_id: int) -> None:
    """
    Replace the stored message IDs of sent digest messages for later cleanup.

    The tracked messages are replaced wholesale, so delete-attempt counters
    from previous cleanup runs are reset.

    Args:
        message_ids: List of Telegram message IDs
        user_id: Target user ID
    """
    data = _load_digest_storage()
    data[str(user_id)] = {
        "message_ids": list(message_ids),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "delete_attempts": {},
    }
    _write_digest_storage(data)


def merge_digest_message_ids(message_ids: List[int], user_id: int) -> None:
    """
    Add newly sent message IDs without discarding IDs still awaiting cleanup.

    When a cleanup run leaves some messages undeleted, those IDs stay in
    storage. Saving the next digest must merge with them (rather than replace)
    so the leftover IDs are still retried by a later cleanup.

    Args:
        message_ids: Message IDs of the digest just sent
        user_id: Target user ID
    """
    data = _load_digest_storage()
    entry = _get_user_entry(data, user_id)
    merged = list(entry["message_ids"])
    for message_id in message_ids:
        if message_id not in merged:
            merged.append(message_id)
    entry["message_ids"] = merged
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    data[str(user_id)] = entry
    _write_digest_storage(data)


def record_digest_delete_failures(failed_ids: List[int], user_id: int) -> List[int]:
    """
    Keep the message IDs whose deletion failed so they are retried later.

    Each failure bumps a per-message attempt counter. Messages that reach
    ``MAX_DIGEST_DELETE_ATTEMPTS`` failures are treated as permanently
    undeletable: they are dropped from storage and not returned for retry.

    Args:
        failed_ids: Message IDs that could not be deleted in this run
        user_id: Target user ID

    Returns:
        The subset of ``failed_ids`` that is still worth retrying.
    """
    data = _load_digest_storage()
    entry = _get_user_entry(data, user_id)
    attempts = entry["delete_attempts"]

    retryable: List[int] = []
    for message_id in failed_ids:
        key = str(message_id)
        attempts[key] = attempts.get(key, 0) + 1
        if attempts[key] < MAX_DIGEST_DELETE_ATTEMPTS:
            retryable.append(message_id)
        else:
            del attempts[key]

    if retryable:
        entry["message_ids"] = retryable
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        data[str(user_id)] = entry
        _write_digest_storage(data)
    else:
        # Nothing left worth retrying - drop the user's entry entirely.
        data.pop(str(user_id), None)
        _write_digest_storage(data)

    return retryable


def get_digest_message_ids(user_id: int) -> List[int]:
    """
    Get stored message IDs for cleanup.

    Args:
        user_id: Target user ID

    Returns:
        List of message IDs
    """
    return list(_get_user_entry(_load_digest_storage(), user_id)["message_ids"])


def clear_digest_message_ids(user_id: int) -> None:
    """
    Clear stored message IDs after cleanup.

    Args:
        user_id: Target user ID
    """
    data = _load_digest_storage()
    if str(user_id) not in data:
        return
    del data[str(user_id)]
    _write_digest_storage(data)
