"""Persistent message storage backends for Telebrief."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import aiosqlite as _aiosqlite
    import asyncpg as _asyncpg  # type: ignore[import-untyped]
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


class StorageBackend(Protocol):
    async def save_messages(self, messages: list[Message]) -> int: ...
    async def close(self) -> None: ...


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

    async def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            await conn.close()


class PostgresBackend:  # pragma: no cover
    def __init__(self, url: str) -> None:
        self._url = url
        self._pool: _asyncpg.Pool | None = None

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
