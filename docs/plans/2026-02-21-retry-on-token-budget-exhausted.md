# Retry on Token Budget Exhausted — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a provider returns empty content because a reasoning model used all tokens on internal reasoning, automatically retry once with 3× the token budget instead of skipping the channel.

**Architecture:** Add a `TokenBudgetExhaustedError` exception (subclass of `RuntimeError`) that all three providers raise instead of a plain `RuntimeError` for the empty+length case. In `_summarize_channel`, catch that specific exception and retry with `self.max_tokens * 3`. If the retry also fails, let the exception propagate normally.

**Tech Stack:** Python 3.10+, pytest + pytest-asyncio, existing `src/ai_providers.py` and `src/summarizer.py`.

---

### Task 1: Write failing tests for `TokenBudgetExhaustedError` in providers

**Files:**
- Modify: `tests/test_ai_providers.py`

**Step 1: Update the import at the top of `tests/test_ai_providers.py`**

The current import (lines 7–12) is:
```python
from src.ai_providers import (  # isort: skip
    _redact_url,
    AnthropicProvider,
    create_provider,
    OllamaProvider,
    OpenAIProvider,
)
```

Change it to:
```python
from src.ai_providers import (  # isort: skip
    _redact_url,
    AnthropicProvider,
    create_provider,
    OllamaProvider,
    OpenAIProvider,
    TokenBudgetExhaustedError,
)
```

**Step 2: Update the three existing empty+length tests to expect `TokenBudgetExhaustedError`**

Find `test_openai_provider_length_empty_content_raises_with_guidance` and change:
```python
        with pytest.raises(RuntimeError) as exc_info:
```
to:
```python
        with pytest.raises(TokenBudgetExhaustedError) as exc_info:
```

Find `test_ollama_provider_length_empty_content_raises_with_guidance` and make the same change.

Find `test_anthropic_provider_max_tokens_empty_content_raises_with_guidance` and make the same change.

**Step 3: Run these three tests to confirm they now FAIL**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && \
  .venv/bin/pytest tests/test_ai_providers.py \
    -k "length_empty_content_raises or max_tokens_empty_content_raises" -v
```

Expected: 3 FAILED (ImportError or `RuntimeError is not TokenBudgetExhaustedError`). This confirms the tests are checking real behaviour.

---

### Task 2: Implement `TokenBudgetExhaustedError` in `src/ai_providers.py`

**Files:**
- Modify: `src/ai_providers.py`

**Step 1: Add the exception class after `_redact_url` and before `AIProvider`**

After the `_redact_url` function, insert:
```python
class TokenBudgetExhaustedError(RuntimeError):
    """Raised when a provider exhausts its token budget without producing visible output."""
```

**Step 2: Update `OpenAIProvider.chat_completion`**

Find the block that raises `RuntimeError` when content is empty and `finish_reason == "length"`:
```python
            if not text:
                if finish_reason == "length":
                    raise RuntimeError(
                        f"OpenAI returned empty content with finish_reason=length — the model "
                        ...
                    )
```

Change `raise RuntimeError(` to `raise TokenBudgetExhaustedError(` for that specific case only. Leave the second `raise RuntimeError(` (the non-length empty case) unchanged.

**Step 3: Update `OllamaProvider.chat_completion`**

Find the equivalent block for `done_reason == "length"`:
```python
        if not text:
            if done_reason == "length":
                raise RuntimeError(
                    f"Ollama returned empty content with done_reason=length — ..."
                )
```

Change `raise RuntimeError(` to `raise TokenBudgetExhaustedError(` for that block only.

**Step 4: Update `AnthropicProvider.chat_completion`**

Find the equivalent block for `stop_reason == "max_tokens"`:
```python
        if not text:
            if stop_reason == "max_tokens":
                raise RuntimeError(
                    f"Anthropic returned empty content with stop_reason=max_tokens — ..."
                )
```

Change `raise RuntimeError(` to `raise TokenBudgetExhaustedError(` for that block only.

**Step 5: Run the three tests again to confirm they now PASS**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && \
  .venv/bin/pytest tests/test_ai_providers.py \
    -k "length_empty_content_raises or max_tokens_empty_content_raises" -v
```

Expected: 3 PASSED.

**Step 6: Run the full ai_providers test file to check for regressions**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && \
  .venv/bin/pytest tests/test_ai_providers.py -v
```

Expected: all green.

**Step 7: Commit**

```bash
git -C /Users/belaytzev/Documents/Sync/Personal/Telebrief add \
  src/ai_providers.py tests/test_ai_providers.py && \
git -C /Users/belaytzev/Documents/Sync/Personal/Telebrief commit -m \
  "feat: add TokenBudgetExhaustedError for empty+length provider responses"
```

---

### Task 3: Write failing tests for retry in `_summarize_channel`

**Files:**
- Modify: `tests/test_summarizer.py`

**Step 1: Add `TokenBudgetExhaustedError` to the import at the top of `tests/test_summarizer.py`**

The current import (line 7) is:
```python
from src.summarizer import ERROR_SUMMARY_PREFIX, Summarizer, SYSTEM_PROMPT_TEMPLATE  # isort: skip
```

Add a second import line right after it:
```python
from src.ai_providers import TokenBudgetExhaustedError  # isort: skip
```

**Step 2: Append three new tests at the end of `tests/test_summarizer.py`**

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_retries_on_token_budget_exhausted(
    sample_config, mock_logger, sample_messages
):
    """_summarize_channel retries with max_tokens*3 when TokenBudgetExhaustedError is raised."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(
            side_effect=[TokenBudgetExhaustedError("budget exhausted"), "Retry summary"]
        )
        result = await summarizer._summarize_channel("Test Channel", sample_messages)

        assert result == "Retry summary"
        assert summarizer.provider.chat_completion.call_count == 2
        first_max = summarizer.provider.chat_completion.call_args_list[0].kwargs["max_tokens"]
        second_max = summarizer.provider.chat_completion.call_args_list[1].kwargs["max_tokens"]
        assert second_max == first_max * 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_retry_failure_propagates(
    sample_config, mock_logger, sample_messages
):
    """_summarize_channel lets the retry exception propagate when the second call also fails."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(
            side_effect=[
                TokenBudgetExhaustedError("budget exhausted"),
                RuntimeError("network error"),
            ]
        )
        with pytest.raises(RuntimeError, match="network error"):
            await summarizer._summarize_channel("Test Channel", sample_messages)

        assert summarizer.provider.chat_completion.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_no_retry_on_success(
    sample_config, mock_logger, sample_messages
):
    """_summarize_channel calls chat_completion exactly once when the first call succeeds."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(return_value="Success summary")

        result = await summarizer._summarize_channel("Test Channel", sample_messages)

        assert result == "Success summary"
        assert summarizer.provider.chat_completion.call_count == 1
```

**Step 3: Run the three new tests to confirm they FAIL**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && \
  .venv/bin/pytest tests/test_summarizer.py \
    -k "retries_on_token_budget or retry_failure_propagates or no_retry_on_success" -v
```

Expected: the first two FAIL (`chat_completion.call_count == 1` instead of 2, retry not implemented). The third may pass accidentally — that's fine.

---

### Task 4: Implement retry in `src/summarizer.py`

**Files:**
- Modify: `src/summarizer.py`

**Step 1: Add `TokenBudgetExhaustedError` to the import**

Find the existing import line:
```python
from src.ai_providers import AIProvider, create_provider
```

Change it to:
```python
from src.ai_providers import AIProvider, TokenBudgetExhaustedError, create_provider
```

**Step 2: Restructure the `try/except` block in `_summarize_channel`**

The current `try` block (inside `_summarize_channel`) is:
```python
        try:
            system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{language}", self.output_language)
            chat_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            summary = await self.provider.chat_completion(
                messages=chat_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            self.logger.debug(f"Summary for {channel_name}: {len(summary)} chars")
            return summary

        except Exception as e:
            self.logger.error(f"AI provider error for {channel_name}: {e}")
            raise
```

Replace it with:
```python
        system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{language}", self.output_language)
        chat_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            summary = await self.provider.chat_completion(
                messages=chat_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except TokenBudgetExhaustedError:
            retry_max_tokens = self.max_tokens * 3
            self.logger.warning(
                "Token budget exhausted for %s; retrying with max_tokens=%d",
                channel_name,
                retry_max_tokens,
            )
            summary = await self.provider.chat_completion(
                messages=chat_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=retry_max_tokens,
            )
        except Exception as e:
            self.logger.error(f"AI provider error for {channel_name}: {e}")
            raise

        self.logger.debug(f"Summary for {channel_name}: {len(summary)} chars")
        return summary
```

**Step 3: Run the three new tests to confirm they now PASS**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && \
  .venv/bin/pytest tests/test_summarizer.py \
    -k "retries_on_token_budget or retry_failure_propagates or no_retry_on_success" -v
```

Expected: 3 PASSED.

**Step 4: Run the full summarizer test file**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && \
  .venv/bin/pytest tests/test_summarizer.py -v
```

Expected: all green.

**Step 5: Commit**

```bash
git -C /Users/belaytzev/Documents/Sync/Personal/Telebrief add \
  src/summarizer.py tests/test_summarizer.py && \
git -C /Users/belaytzev/Documents/Sync/Personal/Telebrief commit -m \
  "feat: retry with 3x token budget on TokenBudgetExhaustedError"
```

---

### Task 5: Full suite and lint

**Step 1: Run the full test suite with coverage**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && make test
```

Expected: all tests pass, coverage ≥ 49%.

**Step 2: Run the linter**

```bash
cd /Users/belaytzev/Documents/Sync/Personal/Telebrief && make lint
```

Expected: no errors. If lint fails, fix the reported issues (typically formatting — run `make format` first, then re-check).

**Step 3: If lint required fixes, commit them**

```bash
git -C /Users/belaytzev/Documents/Sync/Personal/Telebrief add \
  src/ai_providers.py src/summarizer.py && \
git -C /Users/belaytzev/Documents/Sync/Personal/Telebrief commit -m \
  "fix: lint issues after retry implementation"
```
