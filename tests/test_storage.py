"""Tests for src/storage.py"""

import os
from datetime import datetime, timezone

import pytest

from src.collector import Message
from src.config_loader import StorageConfig
from src.storage import SQLiteBackend, create_storage


def _make_message(text: str = "hello", channel: str = "chan") -> Message:
    return Message(
        text=text,
        sender="Alice",
        timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        link="https://t.me/chan/1",
        channel_name=channel,
        has_media=False,
        media_type="",
    )


# ---------------------------------------------------------------------------
# SQLiteBackend
# ---------------------------------------------------------------------------


class TestSQLiteBackend:
    @pytest.mark.asyncio
    async def test_save_messages_returns_count(self, tmp_path):
        db = tmp_path / "test.db"
        backend = SQLiteBackend(str(db))
        await backend.initialize()
        try:
            msgs = [_make_message("a"), _make_message("b")]
            count = await backend.save_messages(msgs)
            assert count == 2
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_save_messages_empty_returns_zero(self, tmp_path):
        db = tmp_path / "test.db"
        backend = SQLiteBackend(str(db))
        await backend.initialize()
        try:
            count = await backend.save_messages([])
            assert count == 0
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_append_only_duplicate_rows(self, tmp_path):
        db = tmp_path / "test.db"
        backend = SQLiteBackend(str(db))
        await backend.initialize()
        try:
            msgs = [_make_message("same")]
            await backend.save_messages(msgs)
            await backend.save_messages(msgs)

            import aiosqlite

            async with aiosqlite.connect(str(db)) as conn:
                async with conn.execute("SELECT count(*) FROM messages") as cur:
                    row = await cur.fetchone()
            assert row[0] == 2
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_close_idempotent(self, tmp_path):
        db = tmp_path / "test.db"
        backend = SQLiteBackend(str(db))
        await backend.initialize()
        await backend.close()
        await backend.close()  # should not raise

    @pytest.mark.asyncio
    async def test_close_safe_when_never_initialized(self, tmp_path):
        db = tmp_path / "test.db"
        backend = SQLiteBackend(str(db))
        await backend.close()  # should not raise

    @pytest.mark.asyncio
    async def test_creates_parent_dirs(self, tmp_path):
        db = tmp_path / "nested" / "deep" / "test.db"
        backend = SQLiteBackend(str(db))
        await backend.initialize()
        await backend.close()
        assert db.exists()


# ---------------------------------------------------------------------------
# create_storage factory
# ---------------------------------------------------------------------------


class TestCreateStorage:
    @pytest.mark.asyncio
    async def test_disabled_returns_none(self):
        cfg = StorageConfig(enabled=False)
        result = await create_storage(cfg)
        assert result is None

    @pytest.mark.asyncio
    async def test_sqlite_returns_ready_backend(self, tmp_path):
        db = tmp_path / "factory.db"
        cfg = StorageConfig(enabled=True, backend="sqlite", path=str(db))
        backend = await create_storage(cfg)
        assert backend is not None
        try:
            count = await backend.save_messages([_make_message()])
            assert count == 1
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_unknown_backend_raises(self):
        cfg = StorageConfig(enabled=True, backend="unknown", path="x.db")
        with pytest.raises(ValueError, match="Unknown storage backend"):
            await create_storage(cfg)
