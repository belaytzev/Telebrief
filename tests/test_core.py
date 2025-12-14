"""Tests for core module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core import generate_and_send_digest, generate_digest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_digest_success(sample_config, mock_logger, sample_messages):
    """Test successful digest generation."""
    # Mock all components
    with patch("src.core.MessageCollector") as mock_collector_class, \
         patch("src.core.Summarizer") as mock_summarizer_class, \
         patch("src.core.DigestFormatter") as mock_formatter_class:

        # Set up mocks
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(
            return_value={"Test Channel": sample_messages}
        )
        mock_collector.disconnect = AsyncMock()
        mock_collector_class.return_value = mock_collector

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={
                "channel_summaries": {"Test Channel": "Summary"},
                "overview": "Overview",
            }
        )
        mock_summarizer_class.return_value = mock_summarizer

        mock_formatter = MagicMock()
        mock_formatter.create_digest = MagicMock(return_value="Formatted digest")
        mock_formatter_class.return_value = mock_formatter

        # Run function
        digest = await generate_digest(sample_config, mock_logger, hours=24)

        # Assertions
        assert digest == "Formatted digest"
        mock_collector.connect.assert_called_once()
        mock_collector.fetch_messages.assert_called_once_with(hours=24)
        mock_collector.disconnect.assert_called_once()
        mock_summarizer.summarize_all.assert_called_once()
        mock_formatter.create_digest.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_digest_collector_error(sample_config, mock_logger):
    """Test error handling in message collection."""
    with patch("src.core.MessageCollector") as mock_collector_class:
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(
            side_effect=Exception("Collection failed")
        )
        mock_collector.disconnect = AsyncMock()
        mock_collector_class.return_value = mock_collector

        with pytest.raises(Exception, match="Collection failed"):
            await generate_digest(sample_config, mock_logger, hours=24)

        # Should still disconnect
        mock_collector.disconnect.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_and_send_digest_success(sample_config, mock_logger, sample_messages):
    """Test successful digest generation and sending."""
    with patch("src.core.MessageCollector") as mock_collector_class, \
         patch("src.core.Summarizer") as mock_summarizer_class, \
         patch("src.core.DigestFormatter") as mock_formatter_class, \
         patch("src.core.DigestSender") as mock_sender_class:

        # Set up mocks
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(
            return_value={"Test Channel": sample_messages}
        )
        mock_collector.disconnect = AsyncMock()
        mock_collector_class.return_value = mock_collector

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={
                "channel_summaries": {"Test Channel": "Summary"},
                "overview": "Overview",
            }
        )
        mock_summarizer_class.return_value = mock_summarizer

        mock_formatter = MagicMock()
        mock_formatter.create_digest = MagicMock(return_value="Formatted digest")
        mock_formatter_class.return_value = mock_formatter

        mock_sender = MagicMock()
        mock_sender.send_digest = AsyncMock(return_value=True)
        mock_sender_class.return_value = mock_sender

        # Run function
        result = await generate_and_send_digest(
            sample_config, mock_logger, hours=24, user_id=123456789
        )

        # Assertions
        assert result is True
        mock_sender.send_digest.assert_called_once_with("Formatted digest", 123456789)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_and_send_digest_send_failure(sample_config, mock_logger, sample_messages):
    """Test handling of send failure."""
    with patch("src.core.MessageCollector") as mock_collector_class, \
         patch("src.core.Summarizer") as mock_summarizer_class, \
         patch("src.core.DigestFormatter") as mock_formatter_class, \
         patch("src.core.DigestSender") as mock_sender_class:

        # Set up mocks (same as success case)
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(
            return_value={"Test Channel": sample_messages}
        )
        mock_collector.disconnect = AsyncMock()
        mock_collector_class.return_value = mock_collector

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={
                "channel_summaries": {"Test Channel": "Summary"},
                "overview": "Overview",
            }
        )
        mock_summarizer_class.return_value = mock_summarizer

        mock_formatter = MagicMock()
        mock_formatter.create_digest = MagicMock(return_value="Formatted digest")
        mock_formatter_class.return_value = mock_formatter

        # Send fails
        mock_sender = MagicMock()
        mock_sender.send_digest = AsyncMock(return_value=False)
        mock_sender_class.return_value = mock_sender

        # Run function
        result = await generate_and_send_digest(
            sample_config, mock_logger, hours=24
        )

        # Should return False
        assert result is False
