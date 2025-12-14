"""
Utility functions and logging setup for Telebrief.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Configure logging format
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Create logger
    logger = logging.getLogger('telebrief')
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
    log_file = f'logs/telebrief.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
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

    return text[:max_length - 100] + "\n\n...\n\n[Сообщение обрезано из-за ограничения длины Telegram]"


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

    for line in text.split('\n'):
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + '\n'
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = line + '\n'

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


def format_cost(tokens_input: int, tokens_output: int, model: str = "gpt-4-turbo-preview") -> str:
    """
    Estimate API cost.

    Args:
        tokens_input: Input token count
        tokens_output: Output token count
        model: OpenAI model name

    Returns:
        Formatted cost string
    """
    # GPT-4-turbo pricing
    if "gpt-4" in model.lower():
        cost_input = tokens_input * 0.01 / 1000
        cost_output = tokens_output * 0.03 / 1000
    else:  # GPT-3.5
        cost_input = tokens_input * 0.001 / 1000
        cost_output = tokens_output * 0.002 / 1000

    total_cost = cost_input + cost_output
    return f"${total_cost:.2f}"
