# Fix Empty OpenAI Summaries

## Overview
- OpenAI provider silently returns empty strings when the API response has `content=None`
- This causes the formatter to skip all channels ("empty or error summary"), resulting in "No valid channel messages to send"
- The fix adds response metadata logging (finish_reason, refusal, token usage), raises errors on empty content instead of silently returning `""`, and increases the `max_tokens_per_summary` default
- Applies consistent diagnostics across all three AI providers (OpenAI, Ollama, Anthropic)

## Context (from discovery)
- Files/components involved:
  - `src/ai_providers.py` — OpenAIProvider, OllamaProvider, AnthropicProvider (primary fix location)
  - `src/config_loader.py` — `max_tokens_per_summary` default value
  - `tests/test_ai_providers.py` — test coverage for providers
  - `tests/test_config_loader.py` — test for default value change
- Related patterns: All providers follow the same `AIProvider` abstract base class with `chat_completion()` method
- Dependencies: `openai` SDK, `aiohttp`

## Development Approach
- **Testing approach**: TDD (tests first)
- Complete each task fully before moving to the next
- Make small, focused changes
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task
- **CRITICAL: all tests must pass before starting next task** — no exceptions
- **CRITICAL: update this plan file when scope changes during implementation**
- Run tests after each change
- Maintain backward compatibility

## Testing Strategy
- **Unit tests**: required for every task (see Development Approach above)
- Mock OpenAI SDK responses with various finish_reason values and content=None scenarios

## Progress Tracking
- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix
- Update plan if implementation deviates from original scope
- Keep plan in sync with actual work done

## Implementation Steps

### Task 1: Add tests for OpenAIProvider empty response handling
- [x] Write test: OpenAI returns content=None with finish_reason="length" → should raise RuntimeError
- [x] Write test: OpenAI returns content="" (empty string) with finish_reason="stop" → should raise RuntimeError
- [x] Write test: OpenAI returns valid content with finish_reason="stop" → should return content (existing behavior)
- [x] Write test: OpenAI response logs finish_reason, usage tokens in debug output
- [x] Run tests — new tests FAIL as expected (TDD red phase confirmed)

### Task 2: Fix OpenAIProvider to log metadata and raise on empty content
- [x] After `await self.client.chat.completions.create(...)`, extract and log: `finish_reason`, `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`
- [x] Log `response.choices[0].message.refusal` if present (OpenAI refusal field)
- [x] Replace silent `return ""` with `raise RuntimeError` when content is None or empty, including finish_reason in error message
- [x] Run tests — 90/90 pass, coverage 55.18%

### Task 3: Add tests for OllamaProvider empty response handling
- [x] Write test: Ollama returns empty `message.content` → should raise RuntimeError
- [x] Write test: Ollama returns missing `message` key → should raise RuntimeError
- [x] Write test: Ollama returns valid content → already covered by existing test
- [x] Run tests — new tests FAIL as expected (TDD red phase confirmed)

### Task 4: Fix OllamaProvider to log metadata and raise on empty content
- [x] Log response metadata: `model`, `eval_count`, `prompt_eval_count` from Ollama response
- [x] Replace silent empty return with `raise RuntimeError` when content is empty
- [x] Updated existing `test_ollama_provider_debug_logging` to expect 3 debug calls (was 2)
- [x] Run tests — 92/92 pass, coverage 55.46%

### Task 5: Add tests for AnthropicProvider empty response handling
- [x] Write test: Anthropic returns empty `content` array → should raise RuntimeError
- [x] Write test: Anthropic returns content blocks with no text → should raise RuntimeError
- [x] Write test: Anthropic response logs stop_reason and usage
- [x] Run tests — new tests FAIL as expected (TDD red phase confirmed)

### Task 6: Fix AnthropicProvider to log metadata and raise on empty content
- [x] Log `stop_reason` and `usage` (input_tokens, output_tokens) from Anthropic response
- [x] Replace silent empty return with `raise RuntimeError` when content is empty
- [x] Run tests — 95/95 pass, coverage 55.71%

### Task 7: Increase max_tokens_per_summary default
- [x] Write test: verify default `max_tokens_per_summary` is 1500 in Settings dataclass
- [x] Change default from 500 to 1500 in `config_loader.py` Settings dataclass (line 32 + line 144)
- [x] Update test fixtures in `conftest.py` (sample_config + temp_config_file)
- [x] Run tests — 96/96 pass, coverage 55.71%

### Task 8: Verify acceptance criteria
- [x] Verify: OpenAIProvider raises on empty content (not silent return)
- [x] Verify: OllamaProvider raises on empty content (not silent return)
- [x] Verify: AnthropicProvider raises on empty content (not silent return)
- [x] Verify: All providers log response metadata at DEBUG level
- [x] Verify: max_tokens_per_summary defaults to 1500
- [x] Run full test suite — 96/96 pass, coverage 55.71%
- [x] Run linter — black, isort, flake8, mypy, vulture clean; pylint 9.58/10
- [x] Verify test coverage meets project standard (55.71% > 49%)

### Task 9: [Final] Update documentation
- [x] Updated config.yaml.example: max_tokens_per_summary 500 → 1500
- [x] README.md — no changes needed (doesn't reference max_tokens_per_summary)

## Technical Details

### OpenAI response structure
```python
response.choices[0].message.content  # None when empty
response.choices[0].finish_reason    # "stop", "length", "content_filter"
response.choices[0].message.refusal  # str if model refused
response.usage.prompt_tokens
response.usage.completion_tokens
response.usage.total_tokens
```

### Ollama response structure
```json
{
  "message": {"role": "assistant", "content": "..."},
  "model": "gpt-5-nano",
  "eval_count": 123,
  "prompt_eval_count": 456
}
```

### Anthropic response structure
```json
{
  "content": [{"type": "text", "text": "..."}],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 123, "output_tokens": 456}
}
```

### Error message format
```
RuntimeError("OpenAI returned empty content (finish_reason=length, prompt_tokens=1234, completion_tokens=0)")
```

## Post-Completion

**Manual verification:**
- Run `/digest` command in Telegram and confirm summaries are generated
- Check logs for new DEBUG-level response metadata
- Test with deliberately low `max_tokens_per_summary` (e.g., 10) to confirm error is raised and logged clearly
