# Extensibility Architecture: Filters, Prompts, Storage Read API, Plugin Loader

## Overview

Make Telebrief easier to fork and extend without modifying core logic. Closes issue #24 (parent: #20).

Current state already ships:

- `StorageBackend` Protocol (SQLite + Postgres) — `src/storage.py`
- `AIProvider` factory — `src/ai_providers.py`
- Per-channel `lookback_hours` and `prompt_extra` — `src/config_loader.py`

Gaps to close:

1. **No filtering hook** — every collected message goes to AI; no pre-LLM filter chain
2. **Hardcoded prompt template** — `SYSTEM_PROMPT_TEMPLATE` baked into `src/summarizer.py:19-78`
3. **No group-level prompt overrides** — `digest_groups` exist but cannot tune the summary prompt
4. **No storage read API** — write-only, blocks issue #20 use case "export channel data for external models"
5. **No plugin loader** — forks must edit `core.py` to inject custom logic

Selected approach (from brainstorm): **Option A — Protocol + Hook surface + dotted-path plugin loader**. Builds on the existing `StorageBackend` Protocol pattern. Rejected: subclass-extension docs (Option B, brittle), event bus / middleware (Option C, overkill).

Output: ADR + 4 phased PRs. Each phase backwards compatible.

**Acceptance criteria**: gaps 1-5 closed, every new config field optional with default, existing `config.yaml.example` runs unchanged, full test suite + mypy + ruff + black + markdownlint pass, coverage ≥49%.

## Context (from discovery)

- **Files involved**:
  - `src/storage.py:63-66` — `StorageBackend` Protocol (extend with `query_messages`)
  - `src/storage.py:69-176` — `SQLiteBackend`, `PostgresBackend` (add query impl)
  - `src/summarizer.py:19-78` — `SYSTEM_PROMPT_TEMPLATE` literal (extract to file)
  - `src/summarizer.py:215-218` — current `prompt_extra` append point (replace with composer)
  - `src/core.py:55-67` — `_collect_messages` (filter chain insertion point)
  - `src/config_loader.py` — `ChannelConfig`, `DigestGroupConfig`, `StorageConfig`, `Settings`, `Config` (extend)
- **Related patterns**:
  - Existing `Protocol` class in `storage.py` with `# noqa: E704` per-line on stubs (see CLAUDE.md flake8 gotcha)
  - `_parse_*` helpers in `config_loader.py` use strict `isinstance` checks and fail-fast `ValueError`
  - Failure isolation pattern in `core.py::_save_to_storage` (log + continue, do not abort digest)
- **Dependencies**: no new third-party packages. Uses `importlib` (stdlib) for plugin loader.
- **Test infra**: `pytest + pytest-asyncio`, `@pytest.mark.asyncio` for async, fixtures in `tests/conftest.py`, coverage threshold 49%

## Development Approach

- **Testing approach**: Regular (code first, then tests) — matches storage-layer plan precedent
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**
- Run `uv run pytest tests/ -v` after each task
- Run `uv run black src/ tests/` and `uv run mypy src/` before committing each phase
- Maintain backwards compatibility: every new config field optional with default; existing configs run unchanged
- Each phase = separate PR

## Testing Strategy

- **Unit tests**:
  - `tests/extensions/test_loader.py` (new)
  - `tests/extensions/test_filters.py` (new)
  - `tests/extensions/test_prompts.py` (new)
  - `tests/test_storage.py` (extend with query tests)
  - `tests/test_config_loader.py` (extend with new field validation)
- SQLite tests: always run, use `tmp_path` fixture
- Postgres tests: gated behind `TELEBRIEF_TEST_PG_URL` (existing pattern)
- All async tests require `@pytest.mark.asyncio`
- No e2e tests needed (no UI involved)

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document blockers with ⚠️ prefix
- Update plan if implementation deviates from original scope
- Keep plan in sync with actual work done

## What Goes Where

- **Implementation Steps** (`[ ]` checkboxes): code, tests, docs inside this repo
- **Post-Completion** (no checkboxes): manual verification, downstream fork updates, follow-up issues

## Implementation Steps

### Phase 1 — Skeleton + ADR + Plugin Loader

#### Task 1: ADR document

**Files:**

- Create: `docs/adr/0001-extensibility-architecture.md`

- [ ] write Context section (issue #20 motivation, issue #24 design questions)
- [ ] write Decision section (Option A: Protocol + dotted-path plugin loader)
- [ ] write Alternatives Rejected section (Option B subclassing, Option C event bus, with reasons)
- [ ] write Consequences section (security note: dotted-path import = arbitrary code execution, equivalent threat model to existing config since YAML already holds API keys; note that filter modules must use `from __future__ import annotations` if importing `ChannelConfig` to avoid import cycles)
- [ ] write Migration section (phased rollout, each phase backwards compatible)
- [ ] verify markdownlint MD031 compliance (blank line before/after fenced code blocks)
- [ ] run pre-commit on edited markdown: `uv run pre-commit run markdownlint --files docs/adr/0001-extensibility-architecture.md`

#### Task 2: Plugin loader helper

**Files:**

- Create: `src/extensions/__init__.py`
- Create: `src/extensions/loader.py`
- Create: `tests/extensions/__init__.py`
- Create: `tests/extensions/test_loader.py`

- [ ] create `src/extensions/__init__.py` (empty)
- [ ] implement `load_class(dotted_path: str) -> type` in `src/extensions/loader.py` using `importlib.import_module` + `getattr`
- [ ] raise `ValueError` with helpful message on missing module / missing attribute / non-class result
- [ ] create `tests/extensions/__init__.py` (empty)
- [ ] write tests in `tests/extensions/test_loader.py`: valid path resolves, missing module raises, missing attr raises, non-class raises
- [ ] run `uv run pytest tests/extensions/ -v` — must pass before next task

### Phase 2 — Filter Protocol + Chain

#### Task 3: MessageFilter Protocol + builtins

**Files:**

- Create: `src/extensions/filters.py`
- Create: `tests/extensions/test_filters.py`

- [ ] define `MessageFilter` Protocol in `src/extensions/filters.py` with `name: str` attribute and `async def filter(self, channel: ChannelConfig, messages: list[Message]) -> list[Message]: ...` (use `# noqa: E704` per CLAUDE.md flake8 rule)
- [ ] implement `KeywordFilter(include: list[str], exclude: list[str])` — case-insensitive substring match on `Message.text`
- [ ] implement `RegexFilter(pattern: str, mode: Literal["include","exclude"])` — compiled once, applied to `Message.text`
- [ ] implement `MinLengthFilter(min_chars: int)` — drops messages shorter than threshold
- [ ] write tests for each builtin: matches, non-matches, empty input, edge cases
- [ ] run `uv run pytest tests/extensions/test_filters.py -v` — must pass before next task

#### Task 4: FilterConfig parsing

**Files:**

- Modify: `src/config_loader.py`
- Modify: `tests/test_config_loader.py`

- [ ] add `FilterSpec` dataclass: `class_path: str`, `config: dict[str, Any]` (kept stylistically consistent with `StorageConfig` / `ChannelConfig` dataclass pattern)
- [ ] add `filters: list[FilterSpec] = field(default_factory=list)` to `Settings`
- [ ] add `filters: list[FilterSpec] | None = None` to `ChannelConfig` (None = use global, `[]` = explicit empty override)
- [ ] implement `_parse_filter_specs(raw_list, path_label)` helper with `isinstance` checks (matches `_parse_storage_config` style)
- [ ] YAML key for the dotted path is `class_path:` (NOT `class:` — Python keyword conflict)
- [ ] wire `_parse_filter_specs` into channel parsing (`_parse_channel_entry`) and global settings parsing
- [ ] structural validation only at config load (string/dict types, required `class_path` field). Class resolution deferred to instantiation time in `core.py::_apply_filters` — avoids importing user code during `load_config()` (which runs in tests, smoke checks, bot startup) and avoids import cycles when filter modules reference `ChannelConfig`.
- [ ] verify `tests/conftest.py` `sample_config` fixture still constructs without changes (every new field has a default)
- [ ] write tests: valid filter spec, invalid type (non-string `class_path`, non-dict `config`), missing `class_path`, per-channel override replaces global, channel `filters: []` is explicit no-op at config layer
- [ ] run `uv run pytest tests/test_config_loader.py -v` — must pass before next task

#### Task 5: Filter chain wiring in core

**Files:**

- Modify: `src/core.py`
- Create: `tests/test_core_filters.py`

- [ ] add `_apply_filters(channel_cfg: ChannelConfig, messages: list[Message], config: Config, logger) -> list[Message]` helper in `src/core.py` (takes full `Config`, reads channel + global filter specs from there)
- [ ] resolve effective filter list: `channel_cfg.filters` if not `None` else `config.settings.filters`
- [ ] instantiate each filter via `load_class(spec.class_path)(**spec.config)` per call (no caching — instantiation cost is negligible vs Telegram + AI calls; avoids cache-invalidation and test-isolation bugs)
- [ ] on `load_class` failure or instantiation error: log + skip that filter, digest continues (matches `_save_to_storage` failure pattern in `core.py:30-44`)
- [ ] apply chain in order; on per-filter `filter()` exception: log + skip that filter; preserve message list as-is for that step
- [ ] call `_apply_filters` inside `_collect_messages` AFTER `collector.fetch_messages` (which already truncates by `lookback_hours`) and BEFORE `_save_to_storage`
- [ ] write tests: chain ordering, empty input short-circuit, exception isolation (one filter fails, others run), per-channel override semantics, default disabled (empty list), channel `filters: []` causes zero filters to apply even when global has filters defined, unresolvable `class_path` is logged + skipped (does not abort digest)
- [ ] run `uv run pytest tests/ -v` — full suite must pass before next task

### Phase 3 — Prompt Composer + Group Binding

#### Task 6: Extract base prompt template

**Files:**

- Create: `src/prompts/__init__.py`
- Create: `src/prompts/base_summary.txt`
- Modify: `src/summarizer.py`
- Modify: `tests/test_summarizer.py`

- [ ] create `src/prompts/__init__.py` (empty)
- [ ] copy `SYSTEM_PROMPT_TEMPLATE` literal verbatim from `src/summarizer.py:19-78` into `src/prompts/base_summary.txt` (keep `{language}` placeholder unchanged — substitution still uses `.replace("{language}", ...)`, NOT `.format()`)
- [ ] add `_load_base_template(path: str) -> str` helper in `src/summarizer.py` using `Path(path).read_text(encoding="utf-8")`. No module-level cache — file read on Summarizer init is cheap; avoids test-isolation bugs.
- [ ] default base template path resolves relative to repo root via `Path(__file__).parent.parent / "prompts" / "base_summary.txt"` so cwd-independent (works from systemd, Docker WORKDIR, pytest)
- [ ] verify Dockerfile / packaging copies `src/prompts/*.txt` into the runtime image (fail-fast if missing — do NOT silently fall back to a literal)
- [ ] replace literal usage at `src/summarizer.py:215` with loaded template (behavior identical at this stage)
- [ ] verify all existing summarizer tests still pass with no behavior change
- [ ] run `uv run pytest tests/test_summarizer.py -v` — must pass before next task

#### Task 7: PromptComposer Protocol + DefaultComposer

**Files:**

- Create: `src/extensions/prompts.py`
- Create: `tests/extensions/test_prompts.py`

- [ ] define `PromptComposer` Protocol in `src/extensions/prompts.py` with `compose(channel: ChannelConfig, group: DigestGroupConfig | None) -> str` (use `# noqa: E704`)
- [ ] implement `DefaultComposer(base_template: str, language: str)` with composition order: base (after `{language}` substitution) → `group.prompt_extra` (if group present and non-empty) → `channel.prompt_extra` (if non-empty), separated by clear `\n\n` blocks
- [ ] write tests: base only, base + channel, base + group, base + group + channel ordering, missing group, missing prompt_extra, language substitution
- [ ] run `uv run pytest tests/extensions/test_prompts.py -v` — must pass before next task

#### Task 8: Group binding in config

**Files:**

- Modify: `src/config_loader.py`
- Modify: `tests/test_config_loader.py`

- [ ] add `prompt_extra: str = ""` field to `DigestGroupConfig`
- [ ] add `group: str | None = None` field to `ChannelConfig`
- [ ] add `PromptsConfig` dataclass: `base_template: str = "src/prompts/base_summary.txt"`, `composer: str = ""` (empty = use `DefaultComposer`)
- [ ] add `prompts: PromptsConfig = field(default_factory=PromptsConfig)` to `Config`
- [ ] implement `_parse_prompts_config(yaml_config)` with `isinstance` checks (matches `_parse_storage_config` style)
- [ ] update `_parse_digest_settings` to read `prompt_extra` per group
- [ ] update `_parse_channel_entry` to read `group` field
- [ ] add cross-validation: every `channels[*].group` value must reference an existing `digest_groups[*].name` OR equal `"Other"` OR equal the localized `group_other` UI string (matches `src/grouper.py` runtime behavior which auto-injects "Other"). Fail-fast `ValueError` listing the bad channel/group.
- [ ] verify `tests/conftest.py` `sample_config` fixture still constructs without changes (every new field has a default)
- [ ] write tests: valid group binding, unknown group rejected, `Other` accepted, localized `group_other` accepted, missing group field is ok, group prompt_extra parsing, prompts section parsing, missing prompts section uses defaults
- [ ] run `uv run pytest tests/test_config_loader.py -v` — must pass before next task

#### Task 9: Wire composer into Summarizer

**Files:**

- Modify: `src/summarizer.py`
- Modify: `tests/test_summarizer.py`

- [ ] in `Summarizer.__init__`, build composer: load base template via `config.prompts.base_template`, instantiate `DefaultComposer` (or load custom via `load_class(config.prompts.composer)` when non-empty)
- [ ] build `channel_name -> DigestGroupConfig | None` map at init using `channels[*].group` and `digest_groups`
- [ ] note: `Summarizer` is currently constructed twice per digest run (`core.py:75`, `core.py:157`) — composer rebuild on each is fine because `_load_base_template` is cheap. Custom composers with expensive `__init__` are forks' responsibility.
- [ ] in `_summarize_channel`, replace lines 215-218 (manual `prompt_extra` append) with `system_prompt = self._composer.compose(channel_cfg, group_cfg)`
- [ ] preserve existing behavior when `group` and `prompt_extra` both unset (default composer returns base only)
- [ ] write tests: summarizer uses composer output, channel without group uses base + channel prompt_extra, channel with group uses base + group + channel prompt_extra
- [ ] run `uv run pytest tests/test_summarizer.py -v` — must pass before next task

### Phase 4 — Storage Read API

#### Task 10: Extend StorageBackend Protocol

**Files:**

- Modify: `src/storage.py`
- Modify: `tests/test_storage.py`

- [ ] add `query_messages(channel: str | None = None, since: datetime | None = None, until: datetime | None = None, limit: int = 1000) -> list[Message]` to `StorageBackend` Protocol (use `# noqa: E704`)
- [ ] implement `query_messages` on `SQLiteBackend`: parameterized SELECT with optional WHERE clauses on `channel_name`, `timestamp`; ORDER BY `timestamp DESC`; LIMIT bound
- [ ] reconstruct `Message` dataclass instances from rows (parse ISO timestamp back to `datetime`)
- [ ] implement `query_messages` on `PostgresBackend`: same logic with `$1, $2, ...` placeholders
- [ ] annotate `PostgresBackend.query_messages` body with `# pragma: no cover` matching the rest of the class (lines 119-162) so coverage stays ≥49% without `TELEBRIEF_TEST_PG_URL`
- [ ] write SQLite tests: empty DB returns `[]`, channel filter, since/until filter combos, limit enforcement, ordering, dataclass reconstruction round-trip (save then query)
- [ ] Postgres tests: gated behind `TELEBRIEF_TEST_PG_URL` env var (existing pattern)
- [ ] run `uv run pytest tests/test_storage.py -v` — must pass before next task

### Phase 5 — Verification + Documentation

#### Task 11: Verify acceptance criteria

- [ ] verify all gaps from Overview are closed (filter chain, prompt composer, group bindings, storage read API, plugin loader)
- [ ] verify backwards compatibility: existing `config.yaml.example` runs unchanged with no new fields set
- [ ] run full test suite: `uv run pytest tests/ -v`
- [ ] run type check: `uv run mypy src/`
- [ ] run lint: `uv tool run ruff check src/ tests/`
- [ ] run formatter: `uv run black src/ tests/` (must use 24.10.0 per CLAUDE.md)
- [ ] verify coverage ≥49%: `uv run pytest --cov=src tests/`

#### Task 12: Update documentation

**Files:**

- Modify: `README.md`
- Modify: `config.yaml.example`
- Modify: `docs/adr/0001-extensibility-architecture.md`
- Modify: `docs/plans/20260430-extensibility-architecture.md` (this plan)

- [ ] create or extend an "Extensibility" section in README.md with subsections: Filters (chain semantics, builtins, custom plugins), Prompts (composition order, base template override), Group binding (`channels[*].group`), Storage queries (`query_messages` API)
- [ ] add commented-out filter / group / prompts examples to `config.yaml.example` using the `src.extensions.filters.*` namespace and `class_path:` YAML key
- [ ] note in ADR which sections shipped (cross-link to PRs)
- [ ] verify `tests/extensions/**` is collected by default pytest run: `uv run pytest tests/extensions/ -v`
- [ ] run pre-commit on edited markdown: `uv run pre-commit run markdownlint --files README.md docs/...`
- [ ] move this plan to `docs/plans/completed/20260430-extensibility-architecture.md`
- [ ] mkdir `docs/plans/completed/` if absent

## Technical Details

### Filter chain insertion point

Inside `src/core.py::_collect_messages`, immediately after `collector.fetch_messages` returns and before `_save_to_storage`:

```text
collect (with lookback_hours truncation)
  → APPLY FILTER CHAIN (NEW)
    → save to DB (filtered set)
    → summarize (filtered set)
```

Rationale: collector stays Telegram-only, storage records only relevant messages, AI sees only relevant messages — single chokepoint avoids divergence.

### Prompt composition order

```text
base template (with {language} substituted)
  + group.prompt_extra (if channel.group set and group has prompt_extra)
  + channel.prompt_extra (if non-empty)
```

Specific overrides general — channel wins last because it is the most specific scope. Empty fields skipped (no trailing whitespace).

### Storage query API shape

`query_messages(channel, since, until, limit)` mirrors common log-query semantics. Uses existing `idx_messages_channel_timestamp` index for both backends. Returns dataclass instances so callers do not deal with backend-specific row tuples.

### Plugin loader semantics

- Dotted path: `pkg.module.ClassName`
- Loader: `importlib.import_module("pkg.module")` + `getattr(module, "ClassName")`
- Validation at config load (fail-fast)
- Instantiation: `cls(**spec.config)` for filters, `cls(base_template, language)` for composer
- Security note in ADR: equivalent threat model to existing YAML (already holds API keys, target user ID)

### Config schema additions (all optional)

```yaml
filters:                      # global filter chain (default: [])
  - class_path: src.extensions.filters.KeywordFilter
    config:
      include: ["job", "remote"]
      exclude: ["nsfw"]

prompts:                      # default: built-in DefaultComposer + bundled template
  base_template: src/prompts/base_summary.txt   # default resolved via Path(__file__) — cwd-independent
  composer: ""                # empty = DefaultComposer; otherwise dotted path (e.g., src.extensions.prompts.MyComposer)

digest_groups:
  - name: Jobs
    description: ...
    prompt_extra: ""          # NEW, default ""

channels:
  - id: "@example"
    name: example
    group: Jobs               # NEW, must reference digest_groups[*].name (or "Other" / localized group_other)
    filters: null             # NEW, null=use global, []=explicit no-op, list=override
    prompt_extra: ""          # existing
    lookback_hours: null      # existing
```

YAML key is `class_path:` (NOT `class:` — Python keyword). Dotted path uses the project's `src.` package root (matches existing imports like `from src.storage import ...`). Class resolution happens at filter-instantiation time inside `core.py::_apply_filters`, NOT at config load — keeps `load_config()` from importing arbitrary user code and avoids import cycles when filter modules reference `ChannelConfig`.

## Post-Completion

*Items requiring manual intervention or external systems — informational only.*

**Manual verification:**

- Run digest end-to-end with a fork-style custom filter (e.g., a small `JobFilter` plugin in a separate package) to validate the loader path works for real third-party code
- Confirm `query_messages` returns expected rows after a real collection run with `storage.enabled: true`

**Follow-up issues to file:**

- Export CLI: `python -m src.export --channel X --since YYYY-MM-DD --format jsonl` — out of scope here, natural extension on top of `query_messages`
- Setuptools entry-points discovery — defer until at least 2-3 third-party plugin packages exist
- Per-group default `lookback_hours` — would require collector-side per-group plumbing, not covered by this plan
