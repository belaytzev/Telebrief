# Limit Prompt Input Size

## Overview

When a Telegram channel has many messages, the AI prompt can grow to 6000+ tokens. With
`max_tokens_per_summary=500` (or even 1500), reasoning models (o1, o3-mini) exhaust the entire
token budget on internal reasoning, leaving zero tokens for visible output. The code correctly
detects the empty response and raises an error — but the channel is then completely skipped and
no digest is sent.

**Fix**: cap the total character size of messages fed to the AI in `_format_messages_for_prompt`.
Select the most recent messages that fit within a configurable `max_prompt_chars` budget. When
messages are truncated, emit a WARNING so the user knows older messages were dropped.

## Context (from discovery)

- **Files involved**: `src/summarizer.py`, `src/config_loader.py`, `config.yaml.example`,
  `tests/test_summarizer.py`, `tests/test_config_loader.py`
- **Root cause**: `_format_messages_for_prompt` feeds ALL messages (up to `max_messages_per_channel=500`,
  each truncated to 500 chars) with no total size guard — producing prompts of 6000+ tokens
- **Triggered by**: reasoning models using all completion tokens on internal reasoning, producing
  empty visible content with `finish_reason=length`
- **Existing per-message truncation**: individual messages are already capped at 500 chars;
  we need an additional total-budget cap across all messages

## Development Approach

- **Testing approach**: TDD — write failing tests first, then implement
- Complete each task fully before moving to the next
- Make small, focused changes
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**
- Run tests after each change
- Maintain backward compatibility

## Testing Strategy

- **Unit tests**: required for every task (see Development Approach above)
- `make test` — full suite with coverage; `make test-fast` — quick run without coverage
- `make lint` — Black, isort, Flake8, MyPy, Pylint, Vulture

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix

## What Goes Where

- **Implementation Steps** (`[ ]` checkboxes): code changes, tests, docs
- **Post-Completion** (no checkboxes): manual verification

## Implementation Steps

### Task 1: Write failing tests for input truncation (TDD)

Tests should fail until Task 3 is implemented.

- [x] in `tests/test_summarizer.py`, add test: when total message chars exceed `max_prompt_chars`,
      only the most recent messages that fit are included (older ones dropped)
- [x] add test: when total chars are within budget, all messages are included unchanged
- [x] add test: a single message that alone exceeds `max_prompt_chars` is still included
      (we never drop the only/most-recent message — per-message truncation already applies)
- [x] add test: a WARNING is logged when messages are truncated due to the budget
- [x] add test: `max_prompt_chars` is wired through `_summarize_channel` (check prompt size
      in a mocked `chat_completion` call)
- [x] run tests — these MUST FAIL (confirms tests are checking real behavior)

### Task 2: Add `max_prompt_chars` to config

- [x] in `src/config_loader.py` `Settings` dataclass, add field:
      `max_prompt_chars: int = 8000`
- [x] in `load_config`, load it: `max_prompt_chars=settings_dict.get("max_prompt_chars", 8000)`
- [x] in `config.yaml.example`, document the new setting under `settings:` with a comment
      explaining its purpose and the 8000-char default
- [x] in `tests/test_config_loader.py`, add test: `max_prompt_chars` defaults to 8000 when not
      in config; add test: custom value from YAML is loaded correctly
- [x] run tests — must pass before task 3

### Task 3: Implement input truncation in `summarizer.py`

- [x] modify `_format_messages_for_prompt(self, messages, max_chars)` to accept a `max_chars`
      parameter (keep backward-compatible default, e.g. `max_chars: int = 8000`)
- [x] implement selection: iterate messages in **reverse** (newest first), accumulate formatted
      lines until the next line would exceed `max_chars`, then stop
- [x] reverse the selected messages back to chronological order before joining
- [x] if any messages were dropped, log a WARNING:
      `"Prompt input truncated: kept %d/%d messages (%d chars) to fit max_prompt_chars=%d"`
- [x] in `_summarize_channel`, pass `self.config.settings.max_prompt_chars` to
      `_format_messages_for_prompt`
- [x] run tests — all tests from Task 1 and Task 2 must now pass

### Task 4: Verify acceptance criteria

- [x] verify: a channel with many messages produces a prompt under `max_prompt_chars` chars
- [x] verify: the WARNING log appears when truncation occurs
- [x] verify: channels that previously failed with "empty content + finish_reason=length" now
      produce a shorter, manageable prompt
- [x] run full test suite: `make test` — must pass with coverage ≥ 49%
- [x] run linter: `make lint` — all issues must be fixed

### Task 5: [Final] Update documentation

- [x] check if README.md mentions `max_tokens_per_summary` or input limits — no changes needed

*Note: ralphex automatically moves completed plans to `docs/plans/completed/`*

## Technical Details

**Budget calculation rationale**:
- Default `max_prompt_chars = 8000` ≈ 2000 tokens of message content
- Plus system prompt (~400 tokens) + user prompt template (~200 tokens) = ~2600 total prompt tokens
- With `max_tokens_per_summary = 1500`, this leaves ample room for reasoning + visible output
- Users with non-reasoning models can raise `max_prompt_chars` if they want more context

**Selection algorithm** (`_format_messages_for_prompt`):
```
selected = []
total = 0
for msg in reversed(messages):
    line = format(msg)            # same per-message formatting as today
    if total + len(line) > max_chars and selected:
        break                     # budget exhausted; never drop the only message
    selected.append(line)
    total += len(line)
return "\n".join(reversed(selected))
```

**Affected config fields**:
```yaml
settings:
  max_prompt_chars: 8000   # max characters of message content fed to AI per channel
                            # ~2000 tokens; increase if using non-reasoning models
```

## Post-Completion

**Manual verification**:
- Run a real digest with a high-traffic channel (many messages) and confirm:
  - WARNING log appears showing how many messages were kept vs. dropped
  - Summary is generated successfully (no "empty content" error)
  - Summary quality is acceptable (covers recent messages)

**Config migration note**:
- Existing `config.yaml` files that don't include `max_prompt_chars` will get the default 8000
  automatically — no user action required
