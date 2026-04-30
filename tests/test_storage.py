"""Tests for src/storage.py"""

import os
import uuid
from datetime import datetime, timezone

import pytest

from src.collector import Message
from src.config_loader import StorageConfig
from src.storage import PostgresBackend, SQLiteBackend, create_storage


def _make_message(
    text: str = "hello",
    channel: str = "chan",
    timestamp: datetime | None = None,
) -> Message:
    return Message(
        text=text,
        sender="Alice",
        timestamp=timestamp or datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
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
    async def test_save_messages_raises_when_not_initialized(self, tmp_path):
        db = tmp_path / "test.db"
        backend = SQLiteBackend(str(db))
        with pytest.raises(RuntimeError, match="not initialized"):
            await backend.save_messages([_make_message()])

    @pytest.mark.asyncio
    async def test_creates_parent_dirs(self, tmp_path):
        db = tmp_path / "nested" / "deep" / "test.db"
        backend = SQLiteBackend(str(db))
        await backend.initialize()
        await backend.close()
        assert db.exists()

    @pytest.mark.asyncio
    async def test_query_empty_db_returns_empty(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            result = await backend.query_messages()
            assert result == []
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_raises_when_not_initialized(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        with pytest.raises(RuntimeError, match="not initialized"):
            await backend.query_messages()

    @pytest.mark.asyncio
    async def test_query_roundtrip(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            msg = _make_message("hello", "testchan")
            await backend.save_messages([msg])
            result = await backend.query_messages()
            assert len(result) == 1
            assert result[0].text == "hello"
            assert result[0].channel_name == "testchan"
            assert result[0].timestamp == msg.timestamp
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_channel_filter(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            await backend.save_messages(
                [
                    _make_message("a", "chan1"),
                    _make_message("b", "chan2"),
                ]
            )
            result = await backend.query_messages(channel="chan1")
            assert len(result) == 1
            assert result[0].text == "a"
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_since_filter(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            early = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            late = datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
            await backend.save_messages(
                [
                    _make_message("old", timestamp=early),
                    _make_message("new", timestamp=late),
                ]
            )
            cutoff = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = await backend.query_messages(since=cutoff)
            assert len(result) == 1
            assert result[0].text == "new"
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_until_filter(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            early = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            late = datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
            await backend.save_messages(
                [
                    _make_message("old", timestamp=early),
                    _make_message("new", timestamp=late),
                ]
            )
            cutoff = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            result = await backend.query_messages(until=cutoff)
            assert len(result) == 1
            assert result[0].text == "old"
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_since_until_combo(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
            t2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
            t3 = datetime(2025, 1, 3, tzinfo=timezone.utc)
            await backend.save_messages(
                [
                    _make_message("a", timestamp=t1),
                    _make_message("b", timestamp=t2),
                    _make_message("c", timestamp=t3),
                ]
            )
            result = await backend.query_messages(
                since=datetime(2025, 1, 1, 12, tzinfo=timezone.utc),
                until=datetime(2025, 1, 2, 12, tzinfo=timezone.utc),
            )
            assert len(result) == 1
            assert result[0].text == "b"
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_limit_enforcement(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            msgs = [_make_message(str(i)) for i in range(10)]
            await backend.save_messages(msgs)
            result = await backend.query_messages(limit=3)
            assert len(result) == 3
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_ordering_desc(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
            t2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
            t3 = datetime(2025, 1, 3, tzinfo=timezone.utc)
            await backend.save_messages(
                [
                    _make_message("a", timestamp=t1),
                    _make_message("b", timestamp=t2),
                    _make_message("c", timestamp=t3),
                ]
            )
            result = await backend.query_messages()
            assert [r.text for r in result] == ["c", "b", "a"]
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_returns_message_dataclass(self, tmp_path):
        backend = SQLiteBackend(str(tmp_path / "q.db"))
        await backend.initialize()
        try:
            await backend.save_messages([_make_message()])
            result = await backend.query_messages()
            assert isinstance(result[0], Message)
            assert result[0].has_media is False
            assert result[0].media_type == ""
        finally:
            await backend.close()


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

    def test_postgres_empty_url_raises_via_config_loader(self, tmp_path, monkeypatch):
        from src.config_loader import load_config

        monkeypatch.setenv("TELEGRAM_API_ID", "12345678")
        monkeypatch.setenv("TELEGRAM_API_HASH", "test_hash")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "channels:\n"
            "  - id: '@test'\n"
            "    name: Test\n"
            "settings:\n"
            "  target_user_id: 123456789\n"
            "storage:\n"
            "  enabled: true\n"
            "  backend: postgres\n"
            "  url: ''\n"
        )
        with pytest.raises(ValueError, match="storage.url must be set"):
            load_config(str(config_file))


# ---------------------------------------------------------------------------
# PostgresBackend (env-gated — requires TELEBRIEF_TEST_PG_URL)
# ---------------------------------------------------------------------------

_PG_URL = os.environ.get("TELEBRIEF_TEST_PG_URL", "")


@pytest.mark.skipif(
    not _PG_URL,
    reason="TELEBRIEF_TEST_PG_URL not set",
)
class TestPostgresBackend:
    def _make_channel(self) -> str:
        return f"test_{uuid.uuid4().hex[:8]}"

    @pytest.mark.asyncio
    async def test_save_messages_returns_count(self):
        ch = self._make_channel()
        backend = PostgresBackend(_PG_URL)
        await backend.initialize()
        try:
            msgs = [_make_message("a", ch), _make_message("b", ch)]
            count = await backend.save_messages(msgs)
            assert count == 2
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_save_messages_empty_returns_zero(self):
        backend = PostgresBackend(_PG_URL)
        await backend.initialize()
        try:
            count = await backend.save_messages([])
            assert count == 0
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_append_only_duplicate_rows(self):
        ch = self._make_channel()
        backend = PostgresBackend(_PG_URL)
        await backend.initialize()
        try:
            msgs = [_make_message("same", ch)]
            await backend.save_messages(msgs)
            await backend.save_messages(msgs)

            async with backend._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT count(*) AS n FROM messages WHERE channel_name = $1", ch
                )
            assert row["n"] == 2
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        backend = PostgresBackend(_PG_URL)
        await backend.initialize()
        await backend.close()
        await backend.close()  # should not raise

    @pytest.mark.asyncio
    async def test_close_safe_when_never_initialized(self):
        backend = PostgresBackend(_PG_URL)
        await backend.close()  # should not raise

    @pytest.mark.asyncio
    async def test_query_empty_returns_empty(self):
        ch = self._make_channel()
        backend = PostgresBackend(_PG_URL)
        await backend.initialize()
        try:
            result = await backend.query_messages(channel=ch)
            assert result == []
        finally:
            await backend.close()

    @pytest.mark.asyncio
    async def test_query_roundtrip(self):
        ch = self._make_channel()
        backend = PostgresBackend(_PG_URL)
        await backend.initialize()
        try:
            await backend.save_messages([_make_message("pg_hello", ch)])
            result = await backend.query_messages(channel=ch)
            assert len(result) == 1
            assert result[0].text == "pg_hello"
            assert isinstance(result[0], Message)
        finally:
            await backend.close()
