# Storage Layer: SQLite (default) + Postgres (advanced)

## Overview

Add a persistent message storage layer so raw collected Telegram messages are written to a database after each collection run. SQLite works out of the box with zero config; Postgres is opt-in via a URL. Closes issue #22.

Issue #22 acceptance criteria:
- Add optional SQLite storage backend in `src/storage.py`
- Write messages to DB after collection in `collector.py` / `core.py`
- Config flag to enable/disable (`storage.enabled`, `storage.path`)
- Keep current in-memory flow unchanged when storage is disabled

Current flow (unchanged when `storage.enabled: false`):
```
collect → summarize → format → send
```

New flow (when enabled):
```
collect → **save to DB** → summarize → format → send
```

**Deduplication contract**: Storage is **append-only** — same message collected in overlapping lookback windows will produce duplicate rows. This is intentional: simplest schema, no hidden logic. Documented in `config.yaml.example`.

## Context (from discovery)

- **Files involved**: `src/collector.py` (Message dataclass), `src/core.py` (`_collect_messages` is the single collection chokepoint used by all orchestration paths), `src/config_loader.py` (Settings/Config dataclasses + `load_config`)
- **Related patterns**: `StorageConfig` follows same dataclass + `field(default_factory=...)` pattern as `DigestGroupConfig`. Config loading uses `_parse_*` helpers with strict `isinstance` type checks (see `_parse_channel_entry`).
- **Dependencies**: `aiosqlite` (new, always installed), `asyncpg` (new, always installed, only used when backend=postgres)
- **Test infra**: `pytest + pytest-asyncio`, `@pytest.mark.asyncio` on all async tests, fixtures in `tests/conftest.py`, coverage threshold 49%

## Development Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**
- Run `uv run pytest tests/ -v` after each task

## Testing Strategy

- **Unit tests**: `tests/test_storage.py` (new), additions to existing config loader tests
- SQLite tests: always run, use `tmp_path` fixture — no external deps
- Postgres tests: gated behind `TELEBRIEF_TEST_PG_URL` env var via `pytest.mark.skipif`
- All async tests require `@pytest.mark.asyncio` decorator
- No e2e tests needed (no UI involved)

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix

## What Goes Where

- **Implementation Steps**: all code, config, and test changes within this repo
- **Post-Completion**: manual smoke test with real Telegram session

---

## Implementation Steps

### Task 1: Add StorageConfig to config_loader.py

**Files:**
- Modify: `src/config_loader.py`

- [x] Add `StorageConfig` dataclass after `DigestGroupConfig`:
  ```python
  @dataclass
  class StorageConfig:
      enabled: bool = False
      backend: str = "sqlite"       # "sqlite" | "postgres"
      path: str = "data/messages.db"
      url: str = ""                 # postgres only
  ```
- [x] Add `_parse_storage_config(yaml_config: dict) -> StorageConfig` helper that:
  - Reads optional top-level `storage:` block (missing = all defaults)
  - Validates each field with `isinstance` checks matching `_parse_channel_entry` style
  - Validates `backend` is `"sqlite"` or `"postgres"` (raises `ValueError` otherwise)
  - Validates `url` is non-empty when `backend == "postgres"` **and** `enabled is True` (raises `ValueError`)
  - Validates `path` is a non-empty string for sqlite
- [x] Add `storage: StorageConfig = field(default_factory=StorageConfig)` to `Config` dataclass
- [x] Call `_parse_storage_config(yaml_config)` in `load_config()` and pass result to `Config(..., storage=storage_config)`
- [x] Write tests for `_parse_storage_config`:
  - Missing `storage:` block → returns defaults (enabled=False, backend="sqlite")
  - `backend: "postgres"` with `enabled: true` and empty `url` → `ValueError`
  - `backend: "invalid"` → `ValueError`
  - `enabled` not bool → `ValueError`
  - `path` empty string → `ValueError`
- [x] Run tests — must pass before Task 2

### Task 2: Create src/storage.py

**Files:**
- Create: `src/storage.py`

**Backend lifecycle contract**: `create_storage()` factory calls `await backend.initialize()` before returning. Caller only needs to call `save_messages()` then `close()`. No separate `initialize()` call needed from outside the factory.

- [x] Define `StorageBackend` as a `typing.Protocol` with:
  - `async def save_messages(self, messages: list[Message]) -> int`
  - `async def close(self) -> None`
- [x] Implement `SQLiteBackend`:
  - `__init__(self, path: str)` — stores path, `self._conn = None`
  - `async def initialize(self)` — creates parent dirs via `Path(self._path).parent.mkdir(parents=True, exist_ok=True)`, opens `aiosqlite` connection, runs CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS
  - `async def save_messages(messages: list[Message]) -> int` — `executemany` insert, commit, return `len(messages)`. Empty list → return 0 immediately.
  - `async def close(self)` — closes connection if open; safe to call if never initialized
  - SQLite schema:
    ```sql
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
    );
    CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp
        ON messages(channel_name, timestamp);
    ```
  - Timestamp stored as `msg.timestamp.isoformat()` (UTC-aware datetimes from collector)
- [x] Implement `PostgresBackend`:
  - `__init__(self, url: str)` — stores url, `self._pool = None`
  - `async def initialize(self)` — creates `asyncpg` pool, runs CREATE TABLE IF NOT EXISTS + INDEX
  - `async def save_messages(...)` — `pool.executemany()` with Postgres params, return count
  - `async def close(self)` — closes pool if open; safe to call if never initialized
  - Postgres schema (same columns, dialect differences):
    ```sql
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
    );
    CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp
        ON messages(channel_name, timestamp);
    ```
  - Timestamp passed as `msg.timestamp` (datetime object with UTC tzinfo)
- [x] Implement `create_storage(config: StorageConfig) -> StorageBackend | None` factory:
  - Returns `None` if `config.enabled` is `False`
  - Instantiates `SQLiteBackend(config.path)` or `PostgresBackend(config.url)`
  - Calls `await backend.initialize()` before returning
  - Raises `ValueError` for unknown `config.backend` value (defensive, parser already validates)
- [x] Write tests in `tests/test_storage.py` (all async tests use `@pytest.mark.asyncio`):
  - `SQLiteBackend`: `save_messages` returns correct count, two saves of same data both stored (append-only), empty list returns 0
  - `SQLiteBackend`: `close()` is safe to call twice (idempotent), safe when never initialized
  - `create_storage`: `enabled=False` → returns `None`
  - `create_storage`: `enabled=True, backend="sqlite"` → returns ready `SQLiteBackend` (can call `save_messages`)
  - `create_storage`: unknown backend string → `ValueError`
- [x] Run tests — must pass before Task 3

### Task 3: Wire storage into _collect_messages()

**Files:**
- Modify: `src/core.py`

Wire at the `_collect_messages()` level — this is the single collection chokepoint used by all orchestration paths (scheduler, bot commands, digest mode). Wiring here avoids duplicating the logic in every caller.

- [x] Import `create_storage` and `StorageConfig` from `src.storage` (or only `create_storage` if `StorageConfig` not needed directly)
- [x] Modify `_collect_messages()` signature to accept `storage_config: StorageConfig` (passed from `config.storage`)
- [x] After `await collector.disconnect()` (inside the `finally`), add storage block:
  ```python
  storage = await create_storage(storage_config)
  if storage:
      try:
          flat = [msg for msgs in messages_by_channel.values() for msg in msgs]
          saved = await storage.save_messages(flat)
          logger.info(f"Stored {saved} messages ({storage_config.backend})")
      except Exception as e:
          logger.error(f"Storage write failed, digest continues: {e}")
      finally:
          await storage.close()
  ```
  Storage failures are logged but **do not abort digest generation**.
- [x] Update all callers of `_collect_messages()` to pass `config.storage`
- [x] Write tests for `_collect_messages` wiring (use `AsyncMock`/`MagicMock`):
  - `storage.enabled=False` → `create_storage` not called (or returns None, no save)
  - `storage.enabled=True` → `save_messages` called with flat message list
  - `save_messages` raises → exception logged, function returns normally (digest not aborted)
  - `close()` called even when `save_messages` raises
- [x] Run tests — must pass before Task 4

### Task 4: Update requirements.txt and config.yaml.example

**Files:**
- Modify: `requirements.txt`
- Modify: `config.yaml.example`

- [x] Add to `requirements.txt` (match existing `>=` pinning style):
  ```
  # Storage backends (aiosqlite for SQLite, asyncpg for Postgres)
  aiosqlite>=0.20.0
  asyncpg>=0.29.0
  ```
- [x] Add commented storage block to `config.yaml.example` after the `api_timeout` line:
  ```yaml
  # Storage — persist raw messages for history / external LLM workflows
  # Note: storage is append-only; overlapping lookback windows produce duplicate rows.
  # storage:
  #   enabled: false
  #   backend: sqlite          # "sqlite" (default, no extra setup) or "postgres"
  #   path: data/messages.db   # sqlite only — relative to project root; mount as volume in Docker
  #   url: ""                  # postgres: postgresql://user:pass@host:5432/db
  ```
- [x] Run tests — must pass before Task 5

### Task 5: Add Postgres tests (env-gated) and tighten coverage

**Files:**
- Modify: `tests/test_storage.py`

- [x] Add `TestPostgresBackend` class at top of file with:
  ```python
  @pytest.mark.skipif(
      not os.environ.get("TELEBRIEF_TEST_PG_URL"),
      reason="TELEBRIEF_TEST_PG_URL not set"
  )
  ```
- [x] Mirror same 3 SQLiteBackend save tests using the env-var URL
- [x] Add `close()` idempotent / safe-when-uninitialized test for `PostgresBackend`
- [x] Add `create_storage` test: `backend="postgres"` with empty url + `enabled=True` → `ValueError` raised by `_parse_storage_config` (test via config loader, not factory directly)
- [x] If CI has no `TELEBRIEF_TEST_PG_URL`, add `# pragma: no cover` to `PostgresBackend.save_messages` body to prevent coverage drop below 49% threshold
- [x] Run tests — must pass before Task 6

### Task 6: Verify acceptance criteria

- [ ] `storage.enabled: false` (default) — existing behavior unchanged, no DB file created, all current tests pass
- [ ] `storage.enabled: true, backend: sqlite` — `data/messages.db` created, `messages` table exists with index `idx_messages_channel_timestamp`
- [ ] `storage.enabled: true, backend: postgres, url: ""` — `ValueError` from `load_config` at startup
- [ ] Storage failure (mock `save_messages` to raise) — digest still completes, error logged
- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Run type check: `uv run mypy src/`
- [ ] Run lint: `uv tool run ruff check src/ tests/`
- [ ] Verify coverage still ≥ 49% (`uv run pytest --cov=src tests/`)

### Task 7: [Final] Move plan and update docs

- [ ] Move this plan: `mkdir -p docs/plans/completed && mv docs/plans/20260430-storage-layer.md docs/plans/completed/`
- [ ] Update `config.yaml.example` comment if anything changed during implementation

---

## Technical Details

**Message dataclass** (from `src/collector.py`):
```python
@dataclass
class Message:
    text: str
    sender: str
    timestamp: datetime   # UTC-aware (collector uses timezone.utc)
    link: str
    channel_name: str
    has_media: bool
    media_type: str
```

**SQLite insert row tuple**:
```python
(msg.channel_name, msg.sender, msg.text,
 msg.timestamp.isoformat(), msg.link,
 int(msg.has_media), msg.media_type)
```

**Postgres insert row tuple**:
```python
(msg.channel_name, msg.sender, msg.text,
 msg.timestamp, msg.link,           # datetime passed directly → TIMESTAMPTZ
 msg.has_media, msg.media_type)
```

**Timezone contract**: Collector imports `timezone` and uses `datetime.now(timezone.utc)` / `timezone.utc` → all `Message.timestamp` values are UTC-aware. SQLite stores as ISO 8601 string with UTC offset; Postgres stores as TIMESTAMPTZ.

**Config loading flow** (follows existing `load_config` pattern):
```python
storage_config = _parse_storage_config(yaml_config)
return Config(..., storage=storage_config)
```

**`_collect_messages` updated signature**:
```python
async def _collect_messages(
    config: Config, logger: logging.Logger, hours: int
) -> dict:
    # ... existing collection ...
    storage = await create_storage(config.storage)
    if storage:
        try:
            flat = [msg for msgs in messages_by_channel.values() for msg in msgs]
            saved = await storage.save_messages(flat)
            logger.info(f"Stored {saved} messages ({config.storage.backend})")
        except Exception as e:
            logger.error(f"Storage write failed, digest continues: {e}")
        finally:
            await storage.close()
    return messages_by_channel
```

## Post-Completion

**Manual smoke test**:
- Enable storage in `config.yaml`, run one digest cycle, confirm DB file exists and contains rows:
  ```bash
  sqlite3 data/messages.db "SELECT count(*), channel_name FROM messages GROUP BY channel_name;"
  ```

**Docker**:
- Mount `data/` as a volume so `messages.db` persists across container restarts:
  ```yaml
  volumes:
    - ./data:/app/data
  ```
