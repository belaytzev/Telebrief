# Fix Token-Limit Truncation Handling in AI Providers

## Overview

When an AI provider hits the token limit (`finish_reason=length` for OpenAI, `stop_reason=max_tokens`
for Anthropic, `done_reason=length` for Ollama), the current code raises `RuntimeError("empty content")`
even when the response contains valid (truncated) text. This causes valid (if partial) summaries to be
discarded entirely instead of used.

**Specific failure observed in logs:**
```
finish_reason=length prompt_tokens=6617 completion_tokens=500 total_tokens=7117
ERROR: OpenAI returned empty content (finish_reason=length, ...)
WARNING: Skipping channel 'Вастрик Селфхостеры🔧': empty or error summary
```

The `completion_tokens=500` (max) with empty content indicates the model (likely a reasoning model)
exhausted all tokens in internal reasoning before producing output text — a genuine but recoverable
error with a clear actionable fix (increase `max_tokens_per_summary`).

**Two cases to handle differently:**
1. `finish_reason=length` + **non-empty content** → return truncated text + log WARNING about truncation
2. `finish_reason=length` + **empty content** → raise RuntimeError with actionable guidance to increase
   `max_tokens_per_summary` in config.yaml

## Context (from discovery)

- **File to fix**: `src/ai_providers.py` (OpenAIProvider, AnthropicProvider, OllamaProvider)
- **File to update**: `tests/test_ai_providers.py` (728 lines, existing tests for all three providers)
- **Existing test** (`test_openai_provider_none_content_raises`): tests `finish_reason=length` +
  `content=None` → expects RuntimeError. This test is correct and must remain passing.
- **Missing tests**: `finish_reason=length` + non-empty content (no existing test), and improved
  error message when content is empty.

## Development Approach

- **Testing approach**: TDD — write failing tests first, then fix code to make them pass
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**
- Run tests after each change

## Testing Strategy

- **Unit tests**: required for every task
- No E2E tests for this change (pure logic change, no UI)

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix

## Implementation Steps

### Task 1: Write failing TDD tests for token-limit truncation (OpenAI)

Write tests that document the desired behavior. These will fail until Task 2 fixes the code.

- [x] add test `test_openai_provider_length_with_content_returns_truncated`:
  `finish_reason=length` + non-empty content → returns text + logs WARNING about truncation
- [x] add test `test_openai_provider_length_empty_content_mentions_max_tokens`:
  `finish_reason=length` + empty content → RuntimeError message mentions `max_tokens_per_summary`
  and/or reasoning token usage
- [x] verify both new tests fail (confirming they test new behavior)
- [x] run existing tests — they must still pass before proceeding

### Task 2: Fix OpenAIProvider to handle `finish_reason=length` correctly

- [x] in `OpenAIProvider.chat_completion`, detect `finish_reason == "length"`
- [x] if content is non-empty: log `WARNING` about truncation (suggest increasing max_tokens_per_summary),
  return the text
- [x] if content is empty: raise `RuntimeError` with message that includes "consider increasing
  max_tokens_per_summary" and "reasoning model may have exhausted token budget"
- [x] run tests — both new tests must now pass, existing tests must still pass

### Task 3: Write failing TDD tests for token-limit truncation (Anthropic)

- [x] add test `test_anthropic_provider_max_tokens_with_content_returns_truncated`:
  `stop_reason=max_tokens` + non-empty content → returns text + logs WARNING
- [x] add test `test_anthropic_provider_max_tokens_empty_content_raises_with_guidance`:
  `stop_reason=max_tokens` + empty content → RuntimeError mentions `max_tokens_per_summary`
- [x] verify both new tests fail
- [x] run existing tests — must still pass

### Task 4: Fix AnthropicProvider to handle `stop_reason=max_tokens` correctly

- [x] in `AnthropicProvider.chat_completion`, detect `stop_reason == "max_tokens"`
- [x] if content is non-empty: log WARNING about truncation, return text
- [x] if content is empty: raise `RuntimeError` with actionable guidance
- [x] run tests — all tests must pass

### Task 5: Write failing TDD tests for token-limit truncation (Ollama)

Ollama returns `done_reason: "length"` in its JSON response when `num_predict` is exhausted.

- [x] add test `test_ollama_provider_length_with_content_returns_truncated`:
  `done_reason=length` + non-empty content → returns text + logs WARNING
- [x] add test `test_ollama_provider_length_empty_content_raises_with_guidance`:
  `done_reason=length` + empty content → RuntimeError mentions `max_tokens_per_summary`
- [x] verify both new tests fail
- [x] run existing tests — must still pass

### Task 6: Fix OllamaProvider to handle `done_reason=length` correctly

- [x] in `OllamaProvider.chat_completion`, extract `done_reason` from JSON response
- [x] if `done_reason == "length"` and content non-empty: log WARNING, return text
- [x] if `done_reason == "length"` and content empty: raise `RuntimeError` with guidance
- [x] update existing debug logging to include `done_reason` in metadata log
- [x] run tests — all tests must pass

### Task 7: Verify acceptance criteria

- [x] run full test suite: `make test` — all tests must pass
- [x] run linter: `make lint` — no new issues
- [x] verify `finish_reason=length` + non-empty content returns text (check test)
- [x] verify `finish_reason=length` + empty content gives actionable error message (check test)
- [x] verify all three providers handle their respective token-limit signals

### Task 8: [Final] Update documentation if needed

- [x] update README.md `max_tokens_per_summary` description if the wording could be clearer
  (only if the config docs don't mention the reasoning-model caveat)

*Note: ralphex automatically moves completed plans to `docs/plans/completed/`*

## Technical Details

### Signal per provider
| Provider  | Token-limit signal        | Equivalent to `finish_reason=length` |
|-----------|--------------------------|--------------------------------------|
| OpenAI    | `finish_reason=length`   | Native field on `Choice` object      |
| Anthropic | `stop_reason=max_tokens` | Field in JSON response               |
| Ollama    | `done_reason=length`     | Field in JSON response data dict     |

### Desired error message (empty-content case)
```
OpenAI returned empty content with finish_reason=length — the model exhausted its token budget
(possibly in reasoning) without producing output. Consider increasing max_tokens_per_summary
in config.yaml. (prompt_tokens=6617, completion_tokens=500)
```

### Desired WARNING (truncated-content case)
```
WARNING: OpenAI response was truncated (finish_reason=length); returning partial content.
Consider increasing max_tokens_per_summary in config.yaml.
```

## Post-Completion

**Manual verification** (if applicable):
- Run a real digest with the configured OpenAI/Anthropic model to confirm summaries are generated
  without errors when `finish_reason=length` produces content
- Check logs to confirm WARNING appears for truncated responses
