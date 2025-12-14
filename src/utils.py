"""
Utility functions and logging setup for Telebrief.
"""

import logging
import os
from datetime import datetime, timedelta


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


def format_timerange(hours: int) -> str:
    """
    Format time range for display.

    Args:
        hours: Number of hours

    Returns:
        Formatted string (e.g., "последние 24ч")
    """
    if hours == 1:
        return "последний 1ч"
    elif hours < 5:
        return f"последние {hours}ч"
    else:
        return f"последние {hours}ч"


def get_lookback_time(hours: int) -> datetime:
    """
    Calculate lookback datetime.

    Args:
        hours: Number of hours to look back

    Returns:
        Datetime object
    """
    return datetime.utcnow() - timedelta(hours=hours)


def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return (
        text[: max_length - 100]
        + "\n\n...\n\n[Сообщение обрезано из-за ограничения длины Telegram]"
    )


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


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    # Rough estimate: 1 token ≈ 4 characters
    return len(text) // 4


def format_cost(tokens_input: int, tokens_output: int, model: str = "gpt-5-nano") -> str:
    """
    Estimate API cost for GPT-5-nano.

    Args:
        tokens_input: Input token count
        tokens_output: Output token count
        model: Model name (only gpt-5-nano supported)

    Returns:
        Formatted cost string
    """
    # GPT-5-nano pricing: $0.050 input, $0.400 output per 1M tokens
    cost_input = tokens_input * 0.050 / 1_000_000
    cost_output = tokens_output * 0.400 / 1_000_000

    total_cost = cost_input + cost_output
    return f"${total_cost:.4f}"
