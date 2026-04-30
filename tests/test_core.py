"""Tests for core module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config_loader import ChannelConfig, FilterSpec, StorageConfig
from src.core import (
    _apply_filters,
    _collect_messages,
    generate_and_send_channel_digests,
    generate_and_send_digest,
    generate_and_send_digest_grouped,
    generate_digest,
)
from src.grouper import GroupedPoint


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_digest_success(sample_config, mock_logger, sample_messages):
    """Test successful digest generation."""
    # Mock all components
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
    ):

        # Set up mocks
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(return_value={"Test Channel": sample_messages})
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
        mock_collector.fetch_messages = AsyncMock(side_effect=Exception("Collection failed"))
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
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
        patch("src.core.DigestSender") as mock_sender_class,
    ):

        # Set up mocks
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(return_value={"Test Channel": sample_messages})
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
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
        patch("src.core.DigestSender") as mock_sender_class,
    ):

        # Set up mocks (same as success case)
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(return_value={"Test Channel": sample_messages})
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
        result = await generate_and_send_digest(sample_config, mock_logger, hours=24)

        # Should return False
        assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_and_send_digest_grouped_success(
    sample_config, mock_logger, sample_messages
):
    """Test digest-grouped flow calls grouper and formatter correctly."""
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestGrouper") as mock_grouper_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
        patch("src.core.DigestSender") as mock_sender_class,
    ):
        # Collector
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(return_value={"Test Channel": sample_messages})
        mock_collector.disconnect = AsyncMock()
        mock_collector_class.return_value = mock_collector

        # Summarizer
        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={
                "channel_summaries": {"Test Channel": "- Point A\n- Point B"},
                "overview": "Overview",
            }
        )
        mock_summarizer_class.return_value = mock_summarizer

        # Grouper
        mock_grouper = MagicMock()
        grouped_result = {
            "News": [GroupedPoint(point="Point A", source="Test Channel")],
            "Other": [GroupedPoint(point="Point B", source="Test Channel")],
        }
        mock_grouper.group_summaries = AsyncMock(return_value=grouped_result)
        mock_grouper_class.return_value = mock_grouper

        # Formatter
        mock_formatter = MagicMock()
        mock_formatter.format_group_message = MagicMock(side_effect=["News msg", "Other msg"])
        mock_formatter.format_group_summary_message = MagicMock(return_value="Summary header")
        mock_formatter_class.return_value = mock_formatter

        # Sender
        mock_sender = MagicMock()
        mock_sender.cleanup_old_digests = AsyncMock()
        mock_sender.send_channel_messages_with_tracking = AsyncMock(return_value=True)
        mock_sender_class.return_value = mock_sender

        result = await generate_and_send_digest_grouped(
            sample_config, mock_logger, hours=24, user_id=123456789
        )

        assert result is True
        mock_grouper.group_summaries.assert_called_once()
        assert mock_formatter.format_group_message.call_count == 2
        mock_formatter.format_group_summary_message.assert_called_once()
        mock_sender.send_channel_messages_with_tracking.assert_called_once()
        # Verify the channel_messages tuples passed to sender
        call_args = mock_sender.send_channel_messages_with_tracking.call_args
        sent_messages = call_args[0][0]
        assert len(sent_messages) == 2
        assert sent_messages[0] == ("News", "News msg")
        assert sent_messages[1] == ("Other", "Other msg")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_and_send_digest_grouped_skips_empty_groups(
    sample_config, mock_logger, sample_messages
):
    """Test that empty groups produce no message."""
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestGrouper") as mock_grouper_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
        patch("src.core.DigestSender") as mock_sender_class,
    ):
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(return_value={"Test Channel": sample_messages})
        mock_collector.disconnect = AsyncMock()
        mock_collector_class.return_value = mock_collector

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={
                "channel_summaries": {"Test Channel": "- Point A"},
                "overview": "Overview",
            }
        )
        mock_summarizer_class.return_value = mock_summarizer

        # Grouper returns one group with points, one empty
        mock_grouper = MagicMock()
        grouped_result = {
            "News": [GroupedPoint(point="Point A", source="Test Channel")],
            "Sport": [],  # empty group
        }
        mock_grouper.group_summaries = AsyncMock(return_value=grouped_result)
        mock_grouper_class.return_value = mock_grouper

        mock_formatter = MagicMock()
        mock_formatter.format_group_message = MagicMock(return_value="News msg")
        mock_formatter.format_group_summary_message = MagicMock(return_value="Summary header")
        mock_formatter_class.return_value = mock_formatter

        mock_sender = MagicMock()
        mock_sender.cleanup_old_digests = AsyncMock()
        mock_sender.send_channel_messages_with_tracking = AsyncMock(return_value=True)
        mock_sender_class.return_value = mock_sender

        result = await generate_and_send_digest_grouped(
            sample_config, mock_logger, hours=24, user_id=123456789
        )

        assert result is True
        # format_group_message called only for News (Sport was empty, skipped)
        mock_formatter.format_group_message.assert_called_once_with(
            group_name="News",
            points=[GroupedPoint(point="Point A", source="Test Channel")],
            hours=24,
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_channel_digests_delegates_to_grouped_when_digest_mode(
    sample_config, mock_logger, sample_messages
):
    """Test mode switch delegates to grouped function when mode is 'digest'."""
    sample_config.settings.digest_mode = "digest"

    with patch("src.core.generate_and_send_digest_grouped", new_callable=AsyncMock) as mock_grouped:
        mock_grouped.return_value = True

        result = await generate_and_send_channel_digests(
            sample_config, mock_logger, hours=12, user_id=999
        )

        assert result is True
        mock_grouped.assert_called_once_with(sample_config, mock_logger, 12, 999)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_channel_digests_uses_per_channel_flow_when_channel_mode(
    sample_config, mock_logger, sample_messages
):
    """Test mode switch uses existing per-channel flow when mode is 'channel'."""
    sample_config.settings.digest_mode = "channel"

    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
        patch("src.core.DigestSender") as mock_sender_class,
        patch("src.core.generate_and_send_digest_grouped", new_callable=AsyncMock) as mock_grouped,
    ):
        mock_collector = MagicMock()
        mock_collector.connect = AsyncMock()
        mock_collector.fetch_messages = AsyncMock(return_value={"Test Channel": sample_messages})
        mock_collector.disconnect = AsyncMock()
        mock_collector_class.return_value = mock_collector

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={
                "channel_summaries": {"Test Channel": "Summary text"},
                "overview": "Overview",
            }
        )
        mock_summarizer_class.return_value = mock_summarizer

        mock_formatter = MagicMock()
        mock_formatter.format_channel_message = MagicMock(return_value="Formatted channel msg")
        mock_formatter.format_summary_message = MagicMock(return_value="Summary")
        mock_formatter_class.return_value = mock_formatter

        mock_sender = MagicMock()
        mock_sender.cleanup_old_digests = AsyncMock()
        mock_sender.send_channel_messages_with_tracking = AsyncMock(return_value=True)
        mock_sender_class.return_value = mock_sender

        result = await generate_and_send_channel_digests(
            sample_config, mock_logger, hours=24, user_id=123456789
        )

        assert result is True
        # Should NOT have delegated to grouped flow
        mock_grouped.assert_not_called()
        # Should have used per-channel formatting
        mock_formatter.format_channel_message.assert_called_once()
        mock_sender.send_channel_messages_with_tracking.assert_called_once()


def _make_collector_mock(sample_messages):
    mock_collector = MagicMock()
    mock_collector.connect = AsyncMock()
    mock_collector.fetch_messages = AsyncMock(return_value={"Test Channel": sample_messages})
    mock_collector.disconnect = AsyncMock()
    return mock_collector


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_messages_storage_disabled(sample_config, mock_logger, sample_messages):
    """storage.enabled=False: create_storage returns None, save_messages never called."""
    sample_config.storage = StorageConfig(enabled=False)
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.return_value = None

        result = await _collect_messages(sample_config, mock_logger, 24)

        mock_create.assert_called_once_with(sample_config.storage)
        assert result == {"Test Channel": sample_messages}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_messages_storage_enabled_saves_flat_list(
    sample_config, mock_logger, sample_messages
):
    """storage.enabled=True: save_messages called with all messages flattened."""
    sample_config.storage = StorageConfig(enabled=True, backend="sqlite", path=":memory:")
    mock_backend = MagicMock()
    mock_backend.save_messages = AsyncMock(return_value=len(sample_messages))
    mock_backend.close = AsyncMock()

    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.return_value = mock_backend

        result = await _collect_messages(sample_config, mock_logger, 24)

        mock_create.assert_called_once_with(sample_config.storage)
        mock_backend.save_messages.assert_called_once_with(sample_messages)
        mock_backend.close.assert_called_once()
        assert result == {"Test Channel": sample_messages}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_messages_storage_error_logged_digest_continues(
    sample_config, mock_logger, sample_messages
):
    """save_messages raises: error logged, _collect_messages still returns messages."""
    sample_config.storage = StorageConfig(enabled=True, backend="sqlite", path=":memory:")
    mock_backend = MagicMock()
    mock_backend.save_messages = AsyncMock(side_effect=RuntimeError("disk full"))
    mock_backend.close = AsyncMock()

    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.return_value = mock_backend

        result = await _collect_messages(sample_config, mock_logger, 24)

        mock_logger.error.assert_called_once()
        assert "RuntimeError" in mock_logger.error.call_args[0][0]
        assert result == {"Test Channel": sample_messages}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_messages_close_called_even_on_save_error(
    sample_config, mock_logger, sample_messages
):
    """close() called in finally even when save_messages raises."""
    sample_config.storage = StorageConfig(enabled=True, backend="sqlite", path=":memory:")
    mock_backend = MagicMock()
    mock_backend.save_messages = AsyncMock(side_effect=RuntimeError("oops"))
    mock_backend.close = AsyncMock()

    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.return_value = mock_backend

        await _collect_messages(sample_config, mock_logger, 24)

        mock_backend.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_messages_storage_init_failure_is_non_fatal(
    sample_config, mock_logger, sample_messages
):
    """create_storage raises: error logged, _collect_messages still returns messages."""
    sample_config.storage = StorageConfig(enabled=True, backend="sqlite", path=":memory:")
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.side_effect = RuntimeError("cannot open db")

        result = await _collect_messages(sample_config, mock_logger, 24)

        mock_logger.error.assert_called_once()
        assert "RuntimeError" in mock_logger.error.call_args[0][0]
        assert result == {"Test Channel": sample_messages}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_digest_calls_storage_when_enabled(
    sample_config, mock_logger, sample_messages
):
    """generate_digest saves messages to storage when enabled."""
    sample_config.storage = StorageConfig(enabled=True, backend="sqlite", path=":memory:")
    mock_backend = MagicMock()
    mock_backend.save_messages = AsyncMock(return_value=len(sample_messages))
    mock_backend.close = AsyncMock()

    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.return_value = mock_backend

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={"channel_summaries": {}, "overview": ""}
        )
        mock_summarizer_class.return_value = mock_summarizer

        mock_formatter = MagicMock()
        mock_formatter.create_digest = MagicMock(return_value="digest")
        mock_formatter_class.return_value = mock_formatter

        await generate_digest(sample_config, mock_logger, hours=24)

        mock_create.assert_called_once_with(sample_config.storage)
        mock_backend.save_messages.assert_called_once_with(sample_messages)
        mock_backend.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_to_storage_close_failure_is_non_fatal(
    sample_config, mock_logger, sample_messages
):
    """storage.close() raises: error logged, no exception propagated."""
    from src.core import _save_to_storage

    sample_config.storage = StorageConfig(enabled=True, backend="sqlite", path=":memory:")
    mock_backend = MagicMock()
    mock_backend.save_messages = AsyncMock(return_value=len(sample_messages))
    mock_backend.close = AsyncMock(side_effect=RuntimeError("close boom"))

    with patch("src.core.create_storage", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_backend
        await _save_to_storage(sample_config, {"Test Channel": sample_messages}, mock_logger)

    mock_logger.error.assert_called()
    error_calls = [str(c) for c in mock_logger.error.call_args_list]
    assert any("close" in c.lower() for c in error_calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_digest_storage_disabled_does_not_save(
    sample_config, mock_logger, sample_messages
):
    """generate_digest skips storage when disabled."""
    sample_config.storage = StorageConfig(enabled=False)
    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.Summarizer") as mock_summarizer_class,
        patch("src.core.DigestFormatter") as mock_formatter_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.return_value = None

        mock_summarizer = MagicMock()
        mock_summarizer.summarize_all = AsyncMock(
            return_value={"channel_summaries": {}, "overview": ""}
        )
        mock_summarizer_class.return_value = mock_summarizer

        mock_formatter = MagicMock()
        mock_formatter.create_digest = MagicMock(return_value="digest")
        mock_formatter_class.return_value = mock_formatter

        await generate_digest(sample_config, mock_logger, hours=24)

        mock_create.assert_called_once_with(sample_config.storage)


# --- _apply_filters tests ---


def _make_filter_spec(class_path: str, **cfg) -> FilterSpec:
    return FilterSpec(class_path=class_path, config=dict(cfg))


class _BrokenFilter:
    name = "broken"

    async def filter(self, channel, messages):
        raise RuntimeError("kaboom")


class _PassFilter:
    name = "pass"

    async def filter(self, channel, messages):
        return messages[:1]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_empty_global_specs_returns_unchanged(
    sample_config, mock_logger, sample_messages
):
    """No global filters configured -> messages unchanged."""
    sample_config.settings.filters = []
    ch_cfg = ChannelConfig(id="@test", name="Test Channel")
    result = await _apply_filters(ch_cfg, sample_messages, sample_config, mock_logger)
    assert result == sample_messages


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_channel_none_uses_global(sample_config, mock_logger, sample_messages):
    """channel.filters=None falls back to global filter list."""
    sample_config.settings.filters = [
        _make_filter_spec("src.extensions.filters.KeywordFilter", include=["message 1"])
    ]
    ch_cfg = ChannelConfig(id="@test", name="Test Channel", filters=None)
    result = await _apply_filters(ch_cfg, sample_messages, sample_config, mock_logger)
    assert len(result) == 1
    assert result[0].text == "Test message 1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_channel_empty_list_overrides_global(
    sample_config, mock_logger, sample_messages
):
    """channel.filters=[] is explicit no-op even when global has filters."""
    sample_config.settings.filters = [
        _make_filter_spec("src.extensions.filters.MinLengthFilter", min_chars=9999)
    ]
    ch_cfg = ChannelConfig(id="@test", name="Test Channel", filters=[])
    result = await _apply_filters(ch_cfg, sample_messages, sample_config, mock_logger)
    assert result == sample_messages


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_channel_list_overrides_global(
    sample_config, mock_logger, sample_messages
):
    """channel.filters with entries overrides global entirely."""
    sample_config.settings.filters = [
        _make_filter_spec("src.extensions.filters.MinLengthFilter", min_chars=9999)
    ]
    ch_cfg = ChannelConfig(
        id="@test",
        name="Test Channel",
        filters=[_make_filter_spec("src.extensions.filters.MinLengthFilter", min_chars=1)],
    )
    result = await _apply_filters(ch_cfg, sample_messages, sample_config, mock_logger)
    assert result == sample_messages


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_chain_ordering(sample_config, mock_logger):
    """Filters apply in order: output of first feeds second."""
    from datetime import datetime, timezone
    from src.collector import Message

    msgs = [
        Message(
            "hello world job", "u", datetime(2025, 1, 1, tzinfo=timezone.utc), "#", "ch", False, ""
        ),
        Message(
            "hello world", "u", datetime(2025, 1, 1, tzinfo=timezone.utc), "#", "ch", False, ""
        ),
        Message(
            "job offer at company",
            "u",
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            "#",
            "ch",
            False,
            "",
        ),
    ]
    sample_config.settings.filters = [
        _make_filter_spec("src.extensions.filters.KeywordFilter", include=["job"]),
        _make_filter_spec("src.extensions.filters.KeywordFilter", exclude=["company"]),
    ]
    ch_cfg = ChannelConfig(id="@test", name="ch")
    result = await _apply_filters(ch_cfg, msgs, sample_config, mock_logger)
    assert len(result) == 1
    assert result[0].text == "hello world job"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_unresolvable_class_path_logged_and_skipped(
    sample_config, mock_logger, sample_messages
):
    """Unresolvable class_path: error logged, filter skipped, messages preserved."""
    sample_config.settings.filters = [
        _make_filter_spec("nonexistent.module.BadFilter"),
    ]
    ch_cfg = ChannelConfig(id="@test", name="Test Channel")
    result = await _apply_filters(ch_cfg, sample_messages, sample_config, mock_logger)
    mock_logger.error.assert_called_once()
    assert "nonexistent.module.BadFilter" in mock_logger.error.call_args[0][0]
    assert result == sample_messages


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_init_error_logged_and_skipped(
    sample_config, mock_logger, sample_messages
):
    """Filter instantiation error: logged, filter skipped, messages preserved."""
    sample_config.settings.filters = [
        _make_filter_spec("src.extensions.filters.MinLengthFilter", min_chars="not_an_int"),
    ]
    ch_cfg = ChannelConfig(id="@test", name="Test Channel")
    result = await _apply_filters(ch_cfg, sample_messages, sample_config, mock_logger)
    mock_logger.error.assert_called_once()
    assert result == sample_messages


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_filters_filter_exception_skips_that_filter_preserves_list(
    sample_config, mock_logger, sample_messages
):
    """filter() raises -> error logged, that step skipped, next filter still runs."""
    sample_config.settings.filters = [
        _make_filter_spec("tests.test_core._BrokenFilter"),
        _make_filter_spec("tests.test_core._PassFilter"),
    ]
    ch_cfg = ChannelConfig(id="@test", name="Test Channel")
    result = await _apply_filters(ch_cfg, sample_messages, sample_config, mock_logger)
    assert len(result) == 1
    mock_logger.error.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_messages_applies_filters_before_storage(
    sample_config, mock_logger, sample_messages
):
    """_collect_messages applies filters; only filtered messages reach storage."""
    sample_config.settings.filters = [
        _make_filter_spec("src.extensions.filters.MinLengthFilter", min_chars=99999)
    ]
    sample_config.storage = StorageConfig(enabled=True, backend="sqlite", path=":memory:")
    mock_backend = MagicMock()
    mock_backend.save_messages = AsyncMock(return_value=0)
    mock_backend.close = AsyncMock()

    with (
        patch("src.core.MessageCollector") as mock_collector_class,
        patch("src.core.create_storage", new_callable=AsyncMock) as mock_create,
    ):
        mock_collector_class.return_value = _make_collector_mock(sample_messages)
        mock_create.return_value = mock_backend

        result = await _collect_messages(sample_config, mock_logger, 24)

    assert result == {"Test Channel": []}
    mock_backend.save_messages.assert_called_once_with([])
