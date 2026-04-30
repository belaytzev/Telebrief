# ADR 0001: Extensibility Architecture — Filters, Prompts, Storage Read API, Plugin Loader

**Status:** Implemented

**Date:** 2026-04-30

**Issues:** #20 (export channel data for external models), #24 (extensibility design)

---

## Context

Telebrief is a Telegram digest generator. As of the storage-layer release (PR #26), the codebase
has a `StorageBackend` Protocol (SQLite + Postgres), an `AIProvider` factory, and per-channel
`lookback_hours`/`prompt_extra` configuration. Five extension points are missing:

1. **No filter chain** — every collected message is sent to the AI; there is no way to drop
   irrelevant messages before summarization without editing `core.py`.
2. **Hardcoded prompt template** — `SYSTEM_PROMPT_TEMPLATE` is a Python string literal baked
   into `src/summarizer.py`. Forks must patch the source file.
3. **No group-level prompt overrides** — `digest_groups` exist for grouping channels in the
   output, but they cannot influence the summary prompt.
4. **No storage read API** — the `StorageBackend` Protocol is write-only. Issue #20 requires
   exporting stored messages to external models.
5. **No plugin loader** — injecting custom filters or composers requires modifying `core.py`
   directly, breaking upgrades.

The goal is to close all five gaps while keeping every new config field optional and
backwards-compatible (existing `config.yaml.example` must run unchanged).

---

## Decision

**Option A: Protocol + Hook Surface + Dotted-Path Plugin Loader**

Extend the existing `StorageBackend` Protocol pattern:

- Define a `MessageFilter` Protocol in `src/extensions/filters.py`.
- Define a `PromptComposer` Protocol in `src/extensions/prompts.py`.
- Add `query_messages` to `StorageBackend` in `src/storage.py`.
- Provide a `load_class(dotted_path: str) -> type` helper in `src/extensions/loader.py`
  using `importlib.import_module` + `getattr`. Class resolution is deferred to runtime
  in `core.py`; it does not happen during `load_config()`.
- Ship built-in implementations: `KeywordFilter`, `RegexFilter`, `MinLengthFilter`,
  `DefaultComposer`.
- All new config fields are optional with safe defaults. YAML key is `class_path:` (not
  `class:` — Python keyword conflict).

Example configuration:

```yaml
filters:
  - class_path: src.extensions.filters.KeywordFilter
    config:
      include: ["job", "remote"]
      exclude: ["nsfw"]

prompts:
  base_template: src/prompts/base_summary.txt
  composer: ""

digest_groups:
  - name: Jobs
    prompt_extra: "Focus on remote positions."

channels:
  - id: "@example"
    group: Jobs
    filters: null
    prompt_extra: ""
    lookback_hours: null
```

Prompt composition order (specific overrides general):

```text
base template (with {language} substituted)
  + group.prompt_extra  (if channel.group set and group has prompt_extra)
  + channel.prompt_extra  (if non-empty)
```

Filter chain insertion point — inside `_collect_messages`, after `fetch_messages`, before
`_save_to_storage`:

```text
collect → APPLY FILTER CHAIN → save to DB → summarize
```

---

## Alternatives Rejected

### Option B: Subclass Extension

Users subclass `Summarizer`, `Collector`, or a new `DigestPipeline` base class to override
behaviour. Rejected because:

- Brittle under refactors — subclasses break when parent signatures change.
- No composition — only one override per class; chaining requires manual `super()` calls.
- Requires exposing internal method signatures as a stable public API, which increases
  maintenance burden.
- Does not solve the filter use case cleanly.

### Option C: Event Bus / Middleware

A central event bus dispatches `message_collected`, `before_summarize`, etc., and plugins
subscribe. Rejected because:

- Overkill for the current scope — Telebrief has a simple linear pipeline.
- Event order and error isolation semantics add complexity without benefit.
- Harder to test than direct Protocol composition.
- Adds a dependency or requires a custom implementation.

---

## Consequences

### Positive

- Forks can inject custom filters and prompt composers via config with no core changes.
- Built-in filters (`KeywordFilter`, `RegexFilter`, `MinLengthFilter`) cover common cases
  without any plugin code.
- `query_messages` unblocks issue #20 export use case and future CLI tooling.
- Pattern is consistent with the existing `StorageBackend` Protocol — low conceptual overhead.

### Negative / Risks

- **Arbitrary code execution:** `load_class("pkg.module.ClassName")` imports and executes
  arbitrary Python. The threat model is equivalent to the existing config file, which already
  holds API keys and target user IDs. Mitigation: document clearly, same trust boundary as
  current config.
- **Import cycles:** filter modules that import `ChannelConfig` must use
  `from __future__ import annotations` to avoid circular imports at load time. Documented in
  `CLAUDE.md` and enforced in code review.
- **No version pinning for plugins:** external packages can break on upgrade. Out of scope;
  follow-up issue will explore setuptools entry-points discovery once the ecosystem matures.

---

## Migration

All changes are phased across four PRs, each backwards-compatible:

| Phase | Scope | Shipped |
|-------|-------|---------|
| 1 | ADR + plugin loader + `MessageFilter` Protocol + builtins + config parsing | branch `extensibility-architecture` (Tasks 1–4) |
| 2 | Filter chain wired into `core.py` | branch `extensibility-architecture` (Task 5) |
| 3 | Prompt extraction + `PromptComposer` Protocol + `DefaultComposer` + group binding | branch `extensibility-architecture` (Tasks 6–9) |
| 4 | `query_messages` storage read API + documentation | branch `extensibility-architecture` (Tasks 10–11) |

Existing `config.yaml.example` runs unchanged throughout. New fields are opt-in.

All tasks shipped on branch `extensibility-architecture`. See plan
`docs/plans/completed/20260430-extensibility-architecture-filters-prompts-storage.md`
for the full task breakdown.
