# Retry on Token Budget Exhausted — Design

## Problem

When a channel is summarized with a reasoning model (e.g. `gpt-5-nano`), the model
spends all of its `max_tokens_per_summary` on internal reasoning and produces empty
visible output. The code correctly detects this (`finish_reason=length` + empty content)
and raises a `RuntimeError`, causing the channel to be skipped entirely in the digest.

Example from logs:
```
finish_reason=length prompt_tokens=3498 completion_tokens=500 total_tokens=3998
ERROR: OpenAI returned empty content with finish_reason=length
```

## Approach

Add a typed `TokenBudgetExhaustedError` exception and a single automatic retry with
a larger token budget.

## Architecture

### `src/ai_providers.py`

- Add `TokenBudgetExhaustedError(RuntimeError)` at module level, carrying
  `prompt_tokens` and `completion_tokens` fields.
- In `OpenAIProvider.chat_completion`: replace the `RuntimeError` for
  `empty content + finish_reason=length` with `TokenBudgetExhaustedError`.
- In `OllamaProvider.chat_completion`: same for `empty content + done_reason=length`.
- In `AnthropicProvider.chat_completion`: same for `empty content + stop_reason=max_tokens`.

### `src/summarizer.py`

- In `_summarize_channel`, after the first `chat_completion` call, catch
  `TokenBudgetExhaustedError`.
- On catch: log a WARNING, then retry once with `max_tokens * 3`.
- If the retry also fails (any exception), let it propagate unchanged.

## Data Flow

```
_summarize_channel
  └─ chat_completion(max_tokens=500)
       └─ [empty + finish_reason=length]
            └─ raises TokenBudgetExhaustedError
  └─ catch TokenBudgetExhaustedError
       └─ log WARNING "Retrying with max_tokens=1500"
       └─ chat_completion(max_tokens=1500)
            └─ returns summary ✓
```

## Scope

- **Files changed**: `src/ai_providers.py`, `src/summarizer.py`,
  `tests/test_summarizer.py`, `tests/test_ai_providers.py`
- **No config changes**: the `* 3` multiplier is an implementation detail
- **No changes to**: `config_loader.py`, `config.yaml.example`, any other file

## Testing

- Unit test: provider raises `TokenBudgetExhaustedError` (not `RuntimeError`) on
  empty+length response
- Unit test: `_summarize_channel` retries with `max_tokens * 3` when
  `TokenBudgetExhaustedError` is raised on the first call
- Unit test: if the retry also fails, the exception propagates (channel still skipped)
- Unit test: successful first call — no retry occurs
