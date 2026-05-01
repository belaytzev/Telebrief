"""Persistent message storage backends for Telebrief."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import aiosqlite as _aiosqlite

    from src.collector import Message
    from src.config_loader import StorageConfig

_CREATE_SQLITE_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name TEXT    NOT NULL,
    sender       TEXT    NOT NULL,
    text         TEXT    NOT NULL,
    timestamp    TEXT    NOT NULL,
    link         TEXT    NOT NULL,
    has_media    INTEGER NOT NULL DEFAULT 0,
    media_type   TEXT    NOT NULL DEFAULT '',
    collected_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
)
"""

_CREATE_SQLITE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp
    ON messages(channel_name, timestamp)
"""

_CREATE_PG_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id           BIGSERIAL PRIMARY KEY,
    channel_name TEXT        NOT NULL,
    sender       TEXT        NOT NULL,
    text         TEXT        NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL,
    link         TEXT        NOT NULL,
    has_media    BOOLEAN     NOT NULL DEFAULT FALSE,
    media_type   TEXT        NOT NULL DEFAULT '',
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

_CREATE_PG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp
    ON messages(channel_name, timestamp)
"""

_SQLITE_INSERT = """
INSERT INTO messages (channel_name, sender, text, timestamp, link, has_media, media_type)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

_PG_INSERT = """
INSERT INTO messages (channel_name, sender, text, timestamp, link, has_media, media_type)
VALUES ($1, $2, $3, $4, $5, $6, $7)
"""

_QUERY_BASE = (
    "SELECT channel_name, sender, text, timestamp, link, has_media, media_type" " FROM messages"
)


class StorageBackend(Protocol):
    async def save_messages(self, messages: list[Message]) -> int: ...  # noqa: E704

    async def close(self) -> None: ...  # noqa: E704

    async def query_messages(  # noqa: E704
        self,
        channel: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 1000,
    ) -> list[Message]: ...


class SQLiteBackend:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: _aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        import aiosqlite

        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        try:
            await self._conn.execute(_CREATE_SQLITE_TABLE)
            await self._conn.execute(_CREATE_SQLITE_INDEX)
            await self._conn.commit()
        except Exception:
            await self._conn.close()
            self._conn = None
            raise

    async def save_messages(self, messages: list[Message]) -> int:
        if self._conn is None:
            raise RuntimeError("SQLiteBackend not initialized; call initialize() first")
        if not messages:
            return 0
        rows = [
            (
                msg.channel_name,
                msg.sender,
                msg.text,
                msg.timestamp.isoformat(),
                msg.link,
                int(msg.has_media),
                msg.media_type,
            )
            for msg in messages
        ]
        try:
            await self._conn.executemany(_SQLITE_INSERT, rows)
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise
        return len(messages)

    async def query_messages(
        self,
        channel: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 1000,
    ) -> list[Message]:
        from src.collector import Message as Msg

        if self._conn is None:
            raise RuntimeError("SQLiteBackend not initialized; call initialize() first")

        for name, dt in (("since", since), ("until", until)):
            if dt is not None and dt.tzinfo is None:
                raise ValueError(f"query_messages: {name!r} must be timezone-aware")

        conditions: list[str] = []
        params: list[Any] = []

        if channel is not None:
            conditions.append("channel_name = ?")
            params.append(channel)
        if since is not None:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())
        if until is not None:
            conditions.append("timestamp < ?")
            params.append(until.isoformat())

        sql = _QUERY_BASE
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows: list[Message] = []
        async with self._conn.execute(sql, params) as cur:
            async for row in cur:
                ts = datetime.fromisoformat(row[3])
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                rows.append(
                    Msg(
                        channel_name=row[0],
                        sender=row[1],
                        text=row[2],
                        timestamp=ts,
                        link=row[4],
                        has_media=bool(row[5]),
                        media_type=row[6],
                    )
                )
        return rows

    async def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            await conn.close()


class PostgresBackend:  # pragma: no cover
    def __init__(self, url: str) -> None:
        self._url = url
        self._pool: Any = None

    async def initialize(self) -> None:
        import asyncpg

        self._pool = await asyncpg.create_pool(self._url)
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(_CREATE_PG_TABLE)
                await conn.execute(_CREATE_PG_INDEX)
        except Exception:
            await self._pool.close()
            self._pool = None
            raise

    async def save_messages(self, messages: list[Message]) -> int:
        if self._pool is None:
            raise RuntimeError("PostgresBackend not initialized; call initialize() first")
        if not messages:
            return 0
        rows = [
            (
                msg.channel_name,
                msg.sender,
                msg.text,
                msg.timestamp,
                msg.link,
                msg.has_media,
                msg.media_type,
            )
            for msg in messages
        ]
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(_PG_INSERT, rows)
        return len(messages)

    async def query_messages(  # pragma: no cover
        self,
        channel: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 1000,
    ) -> list[Message]:  # pragma: no cover
        from src.collector import Message as Msg  # pragma: no cover

        if self._pool is None:  # pragma: no cover
            raise RuntimeError(  # pragma: no cover
                "PostgresBackend not initialized; call initialize() first"
            )

        for name, dt in (("since", since), ("until", until)):  # pragma: no cover
            if dt is not None and dt.tzinfo is None:  # pragma: no cover
                raise ValueError(
                    f"query_messages: {name!r} must be timezone-aware"
                )  # pragma: no cover

        conditions: list[str] = []  # pragma: no cover
        args: list[Any] = []  # pragma: no cover
        idx = 1  # pragma: no cover

        if channel is not None:  # pragma: no cover
            conditions.append(f"channel_name = ${idx}")  # pragma: no cover
            args.append(channel)  # pragma: no cover
            idx += 1  # pragma: no cover
        if since is not None:  # pragma: no cover
            conditions.append(f"timestamp >= ${idx}")  # pragma: no cover
            args.append(since)  # pragma: no cover
            idx += 1  # pragma: no cover
        if until is not None:  # pragma: no cover
            conditions.append(f"timestamp < ${idx}")  # pragma: no cover
            args.append(until)  # pragma: no cover
            idx += 1  # pragma: no cover

        sql = _QUERY_BASE  # pragma: no cover
        if conditions:  # pragma: no cover
            sql += " WHERE " + " AND ".join(conditions)  # pragma: no cover
        sql += f" ORDER BY timestamp DESC LIMIT ${idx}"  # pragma: no cover
        args.append(limit)  # pragma: no cover

        async with self._pool.acquire() as conn:  # pragma: no cover
            records = await conn.fetch(sql, *args)  # pragma: no cover

        result: list[Message] = []  # pragma: no cover
        for r in records:  # pragma: no cover
            ts: datetime = r["timestamp"]  # pragma: no cover
            if ts.tzinfo is None:  # pragma: no cover
                ts = ts.replace(tzinfo=timezone.utc)  # pragma: no cover
            result.append(  # pragma: no cover
                Msg(
                    channel_name=r["channel_name"],
                    sender=r["sender"],
                    text=r["text"],
                    timestamp=ts,
                    link=r["link"],
                    has_media=bool(r["has_media"]),
                    media_type=r["media_type"],
                )
            )
        return result  # pragma: no cover

    async def close(self) -> None:
        pool, self._pool = self._pool, None
        if pool is not None:
            await pool.close()


async def create_storage(config: StorageConfig) -> StorageBackend | None:
    if not config.enabled:
        return None
    if config.backend == "sqlite":
        sqlite_backend = SQLiteBackend(config.path)
        await sqlite_backend.initialize()
        return sqlite_backend
    if config.backend == "postgres":  # pragma: no cover
        pg_backend = PostgresBackend(config.url)  # pragma: no cover
        await pg_backend.initialize()  # pragma: no cover
        return pg_backend  # pragma: no cover
    raise ValueError(f"Unknown storage backend: {config.backend!r}")
