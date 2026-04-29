"""Persistent message storage backends for Telebrief."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
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
        self._conn = None

    async def initialize(self) -> None:
        import aiosqlite

        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        await self._conn.execute(_CREATE_SQLITE_TABLE)
        await self._conn.execute(_CREATE_SQLITE_INDEX)
        await self._conn.commit()

    async def save_messages(self, messages: list[Message]) -> int:
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
        await self._conn.executemany(_SQLITE_INSERT, rows)
        await self._conn.commit()
        return len(messages)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None


class PostgresBackend:  # pragma: no cover
    def __init__(self, url: str) -> None:
        self._url = url
        self._pool = None

    async def initialize(self) -> None:
        import asyncpg  # pragma: no cover

        self._pool = await asyncpg.create_pool(self._url)  # pragma: no cover
        async with self._pool.acquire() as conn:  # pragma: no cover
            await conn.execute(_CREATE_PG_TABLE)  # pragma: no cover
            await conn.execute(_CREATE_PG_INDEX)  # pragma: no cover

    async def save_messages(self, messages: list[Message]) -> int:  # pragma: no cover
        if not messages:  # pragma: no cover
            return 0  # pragma: no cover
        rows = [  # pragma: no cover
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
        async with self._pool.acquire() as conn:  # pragma: no cover
            await conn.executemany(_PG_INSERT, rows)  # pragma: no cover
        return len(messages)  # pragma: no cover

    async def close(self) -> None:  # pragma: no cover
        if self._pool is not None:  # pragma: no cover
            await self._pool.close()  # pragma: no cover
            self._pool = None  # pragma: no cover


async def create_storage(config: StorageConfig) -> StorageBackend | None:
    if not config.enabled:
        return None
    if config.backend == "sqlite":
        backend: StorageBackend = SQLiteBackend(config.path)
        await backend.initialize()  # type: ignore[attr-defined]
        return backend
    if config.backend == "postgres":
        backend = PostgresBackend(config.url)
        await backend.initialize()  # type: ignore[attr-defined]
        return backend
    raise ValueError(f"Unknown storage backend: {config.backend!r}")
