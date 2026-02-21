# Fix Ollama Summarization Error

## Overview

Fix the error that occurs when using Ollama as the AI provider for summarization. The summarization process finishes with an error instead of producing a valid summary.

## Context

- Files involved:
  - `src/ai_providers.py` - OllamaProvider.chat_completion() - primary bug location
  - `src/config_loader.py` - api_timeout default value
  - `config.yaml.example` - example configuration
  - `tests/test_ai_providers.py` - Ollama provider tests
- Related patterns: AnthropicProvider uses the same aiohttp pattern (same fix needed)
- Dependencies: aiohttp (existing)

## Root Cause

Ollama's `/api/chat` endpoint returns responses with `Content-Type: application/x-ndjson` even when `stream: false` is set. aiohttp's `resp.json()` method is strict about content types and raises `aiohttp.ContentTypeError` when the response content type is not `application/json`. This causes every Ollama API call to fail.

Secondary issue: The default `api_timeout` in config is 30 seconds, which is often too short for local Ollama model inference (especially on first load or with larger models).

## Development Approach

- **Testing approach**: TDD - write a failing test first, then fix the code
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Implementation Steps

### Task 1: Fix aiohttp content_type error in OllamaProvider

**Files:**
- Modify: `src/ai_providers.py`
- Modify: `tests/test_ai_providers.py`

- [x] Add a test in `test_ai_providers.py` that simulates Ollama returning `application/x-ndjson` content type - verify it currently fails with ContentTypeError
- [x] Fix `OllamaProvider.chat_completion()` at line 99: change `await resp.json()` to `await resp.json(content_type=None)` to bypass aiohttp's strict content-type check
- [x] Apply the same fix to `AnthropicProvider.chat_completion()` at line 149 for robustness (same pattern, same potential issue)
- [x] Run `source .venv/bin/activate && make test` - must pass before task 2

### Task 2: Increase default api_timeout for Ollama

**Files:**
- Modify: `src/ai_providers.py`
- Modify: `config.yaml.example`
- Modify: `tests/test_ai_providers.py`

- [x] Update `OllamaProvider.__init__()` default timeout from 120 to 300 seconds (5 minutes) to handle slow local models and first-load cold starts
- [x] In `create_provider()`, when provider is `ollama`, use `max(api_timeout, 120)` to ensure Ollama always gets at least 120 seconds regardless of the global config setting
- [x] Update `config.yaml.example` to add a comment noting that Ollama may need higher timeouts (e.g., 120-300) for local models
- [x] Add a test verifying that Ollama provider gets at least 120 second timeout even when a lower api_timeout is configured
- [x] Run `source .venv/bin/activate && make test` - must pass before task 3

### Task 3: Improve error logging for debugging

**Files:**
- Modify: `src/ai_providers.py`

- [x] Add debug-level logging in `OllamaProvider.chat_completion()` before the HTTP call: log the Ollama URL, model name, and timeout value
- [x] Add debug-level logging after successful response: log response status and content length
- [x] Run `source .venv/bin/activate && make test` - must pass before task 4

### Task 4: Verify acceptance criteria

- [ ] Run full test suite: `source .venv/bin/activate && make test`
- [ ] Run linter: `source .venv/bin/activate && make lint`
- [ ] Verify that the OllamaProvider test with mocked `application/x-ndjson` content type passes
- [ ] Verify that timeout enforcement test passes
- [ ] Verify test coverage meets 80%+

### Task 5: Update documentation

- [ ] Move this plan to `docs/plans/completed/`
