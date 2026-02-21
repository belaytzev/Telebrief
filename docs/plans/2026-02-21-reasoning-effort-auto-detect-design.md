# Auto-Detect Reasoning Models and Suppress Reasoning Effort

## Overview

Reasoning models (e.g. `gpt-5-nano`) consume completion tokens on internal reasoning before
producing visible output. With a ~3400-token prompt and a 1500-token completion cap, the model
exhausts its budget on reasoning and returns empty content — causing the channel to be skipped.

**Fix**: on the existing `TokenBudgetExhaustedError` retry, also pass `reasoning_effort="low"` to
suppress unnecessary internal reasoning for a summarization task. If the model does not support
the parameter, fall back silently to the plain token-scaled retry.

## Context

- **Trigger**: `finish_reason=length` + empty content → `TokenBudgetExhaustedError`
- **Current retry**: attempt 1 (500 tokens) → fail → attempt 2 (1500 tokens) → fail → error
- **Root cause**: reasoning models spend all completion tokens on reasoning, leaving none for output
- **Provider**: OpenAI supports `reasoning_effort` (`"low"` / `"medium"` / `"high"`);
  Anthropic and Ollama do not

## Retry Flow (after change)

```
attempt 1: normal (max_tokens=500)
    → TokenBudgetExhausted
attempt 2: max_tokens=1500, reasoning_effort="low"
    → API rejects reasoning_effort? → fallback: max_tokens=1500, no reasoning_effort
    → still TokenBudgetExhausted → error (channel skipped, as today)
```

## Components

### `src/ai_providers.py`

- Add `reasoning_effort: str | None = None` to the `chat_completion` interface (base class /
  protocol)
- **OpenAI provider**: pass `reasoning_effort` to the API call when non-None
- **Anthropic provider**: accept and ignore the parameter
- **Ollama provider**: accept and ignore the parameter

### `src/summarizer.py`

- In `_summarize_channel`, the retry call adds `reasoning_effort="low"`
- Wrap the retry in an inner try/except for API errors caused by unsupported parameters:
  catch, log at DEBUG ("Model does not support reasoning_effort, retrying without it"),
  then retry once more without the parameter
- No config changes — fully automatic and transparent to the user

## Error Handling

| Scenario | Behaviour |
|---|---|
| Retry with `reasoning_effort="low"` succeeds | Normal output, no change |
| API rejects `reasoning_effort` | Catch, DEBUG log, retry without it |
| Both retries exhaust token budget | Existing error path — channel skipped |

## Testing Strategy

- **TDD**: write failing tests first, then implement
- Test that retry passes `reasoning_effort="low"` to `chat_completion` on `TokenBudgetExhaustedError`
- Test that API rejection of `reasoning_effort` triggers silent fallback (no reasoning_effort param)
- Test that Anthropic and Ollama providers accept the parameter without error
- Test that double exhaustion still results in channel being skipped (existing behaviour preserved)

## Development Approach

- Small, focused changes; complete each task before moving to the next
- Every task must include new/updated tests; all tests must pass before starting the next task
- `make test` — full suite; `make test-fast` — quick run; `make lint` — full lint
