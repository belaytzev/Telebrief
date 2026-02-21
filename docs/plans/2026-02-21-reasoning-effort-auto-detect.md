# Reasoning Effort Auto-Detect Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a reasoning model exhausts its token budget (empty content + `finish_reason=length`), automatically retry with `reasoning_effort="low"` to suppress unnecessary internal reasoning for a summarization task; if the model rejects the parameter, silently fall back to the plain token-scaled retry.

**Architecture:** Add optional `reasoning_effort: str | None = None` to the `chat_completion` interface. `OpenAIProvider` passes it to the API and handles `BadRequestError` (unsupported param) by retrying without it. Anthropic and Ollama providers accept and ignore it. `_summarize_channel` in the summarizer passes `reasoning_effort="low"` on the existing 3× token retry.

**Tech Stack:** Python 3.10+, openai SDK v1 (`BadRequestError`, `httpx.Response`), pytest + `pytest-asyncio`, `unittest.mock`

---

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix

## What Goes Where

- **Implementation Steps** (`[ ]` checkboxes): code changes, tests, docs
- **Post-Completion** (no checkboxes): manual verification

---

## Implementation Steps

### Task 1: Write failing tests for OpenAI provider `reasoning_effort`

**Files:**
- Modify: `tests/test_ai_providers.py`

Tests must FAIL until Task 3 is implemented.

**Step 1: Open `tests/test_ai_providers.py` and append these three tests after the existing OpenAI tests**

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_passes_reasoning_effort_when_provided(mock_logger):
    """OpenAI provider passes reasoning_effort to the API when a value is given."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_choice = MagicMock()
        mock_choice.message.content = "Summary"
        mock_choice.message.refusal = None
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=500,
            reasoning_effort="low",
        )

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert call_kwargs.get("reasoning_effort") == "low"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_omits_reasoning_effort_when_none(mock_logger):
    """OpenAI provider does NOT include reasoning_effort in the API call when it is None."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="response", refusal=None),
                                           finish_reason="stop")]
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=500,
            reasoning_effort=None,
        )

        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "reasoning_effort" not in call_kwargs


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_falls_back_when_reasoning_effort_rejected(mock_logger):
    """When the API rejects reasoning_effort (BadRequestError), the provider retries without it."""
    import httpx
    from openai import BadRequestError

    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_choice = MagicMock()
        mock_choice.message.content = "Summary without reasoning"
        mock_choice.message.refusal = None
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        bad_request = BadRequestError(
            message="Unsupported parameter: reasoning_effort",
            response=httpx.Response(
                400,
                json={"error": {"message": "Unsupported parameter: reasoning_effort"}},
            ),
            body={"error": {"message": "Unsupported parameter: reasoning_effort"}},
        )

        provider.client.chat.completions.create = AsyncMock(
            side_effect=[bad_request, mock_response]
        )

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=500,
            reasoning_effort="low",
        )

        assert result == "Summary without reasoning"
        assert provider.client.chat.completions.create.call_count == 2

        second_call_kwargs = provider.client.chat.completions.create.call_args_list[1][1]
        assert "reasoning_effort" not in second_call_kwargs

        debug_calls = " ".join(str(c) for c in mock_logger.debug.call_args_list)
        assert "reasoning_effort" in debug_calls.lower()
```

**Step 2: Run just the new tests to confirm they FAIL**

```
make test-fast 2>&1 | grep -E "(PASSED|FAILED|ERROR|reasoning_effort)"
```

Expected: all three new tests FAIL with `TypeError` (unexpected keyword argument).

**Step 3: Commit the failing tests**

```bash
git add tests/test_ai_providers.py
git commit -m "test: add failing tests for reasoning_effort in OpenAI provider"
```

---

### Task 2: Write failing tests for Anthropic/Ollama providers and summarizer retry

**Files:**
- Modify: `tests/test_ai_providers.py`
- Modify: `tests/test_summarizer.py`

**Step 1: Append Anthropic and Ollama tests to `tests/test_ai_providers.py`**

After the existing Anthropic tests, add:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_anthropic_provider_accepts_reasoning_effort_param(mock_logger):
    """Anthropic provider silently accepts and ignores reasoning_effort."""
    provider = AnthropicProvider(api_key="sk-ant-test", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"content": [{"type": "text", "text": "response"}],
                      "stop_reason": "end_turn",
                      "usage": {"input_tokens": 100, "output_tokens": 50}}
    )
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4-6",
            temperature=0.7,
            max_tokens=500,
            reasoning_effort="low",
        )

    assert result == "response"
```

After the existing Ollama tests, add:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_accepts_reasoning_effort_param(mock_logger):
    """Ollama provider silently accepts and ignores reasoning_effort."""
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content_length = 42
    mock_response.json = AsyncMock(return_value={"message": {"content": "response"}})
    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="llama3",
            temperature=0.7,
            max_tokens=500,
            reasoning_effort="low",
        )

    assert result == "response"
```

**Step 2: Update the existing retry test in `tests/test_summarizer.py` to also assert `reasoning_effort="low"`**

Find `test_summarize_channel_retries_on_token_budget_exhausted` and add one assertion at the end:

```python
        assert second_max == first_max * 3
        # NEW: retry must include reasoning_effort="low"
        second_kwargs = summarizer.provider.chat_completion.call_args_list[1].kwargs
        assert second_kwargs.get("reasoning_effort") == "low"
```

**Step 3: Add a new dedicated test for reasoning_effort on retry**

Append to `tests/test_summarizer.py`:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_summarize_channel_retry_passes_reasoning_effort_low(
    sample_config, mock_logger, sample_messages
):
    """On retry after TokenBudgetExhaustedError, reasoning_effort='low' is passed."""
    with patch("src.ai_providers.AsyncOpenAI"):
        summarizer = Summarizer(sample_config, mock_logger)
        summarizer.provider.chat_completion = AsyncMock(
            side_effect=[TokenBudgetExhaustedError("budget"), "Retry summary"]
        )

        result = await summarizer._summarize_channel("Test Channel", sample_messages)

        assert result == "Retry summary"
        retry_kwargs = summarizer.provider.chat_completion.call_args_list[1].kwargs
        assert retry_kwargs.get("reasoning_effort") == "low"
```

**Step 4: Run tests to confirm new ones fail**

```
make test-fast 2>&1 | grep -E "(PASSED|FAILED|ERROR|reasoning_effort)"
```

Expected: all five new/updated tests FAIL.

**Step 5: Commit**

```bash
git add tests/test_ai_providers.py tests/test_summarizer.py
git commit -m "test: add failing tests for reasoning_effort in Anthropic, Ollama, and summarizer retry"
```

---

### Task 3: Implement `reasoning_effort` in `src/ai_providers.py`

**Files:**
- Modify: `src/ai_providers.py`

**Step 1: Add `BadRequestError` to the openai import (line 14)**

Change:
```python
from openai import AsyncOpenAI
```
to:
```python
from openai import AsyncOpenAI, BadRequestError as OpenAIBadRequestError
```

**Step 2: Add `reasoning_effort` to the abstract base class signature (around line 36)**

Change:
```python
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
```
to:
```python
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None = None,
    ) -> str:
```

**Step 3: Rewrite `OpenAIProvider.chat_completion` to use kwargs dict and handle `BadRequestError` (around line 67)**

Replace the entire method body with:

```python
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None = None,
    ) -> str:
        create_kwargs: Dict[str, Any] = dict(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_completion_tokens=max_tokens,
        )
        if reasoning_effort is not None:
            create_kwargs["reasoning_effort"] = reasoning_effort

        try:
            response = await self.client.chat.completions.create(**create_kwargs)
        except OpenAIBadRequestError as exc:
            if reasoning_effort is not None:
                self.logger.debug(
                    "reasoning_effort=%r rejected by model, retrying without it: %s",
                    reasoning_effort,
                    exc,
                )
                create_kwargs.pop("reasoning_effort")
                response = await self.client.chat.completions.create(**create_kwargs)
            else:
                raise

        if not response.choices:
            raise RuntimeError("OpenAI returned no choices in response")

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        refusal = getattr(choice.message, "refusal", None)
        usage = response.usage

        self.logger.debug(
            "OpenAI response: finish_reason=%s prompt_tokens=%s "
            "completion_tokens=%s total_tokens=%s",
            finish_reason,
            usage.prompt_tokens if usage else None,
            usage.completion_tokens if usage else None,
            usage.total_tokens if usage else None,
        )

        if refusal:
            self.logger.warning("OpenAI model refusal: %s", refusal)

        content = choice.message.content
        text = content.strip() if content else ""
        if not text:
            if finish_reason == "length":
                raise TokenBudgetExhaustedError(
                    f"OpenAI returned empty content with finish_reason=length — the model "
                    f"exhausted its token budget (possibly in reasoning) without producing output. "
                    f"Consider increasing max_tokens_per_summary in config.yaml. "
                    f"(prompt_tokens={usage.prompt_tokens if usage else 'N/A'}, "
                    f"completion_tokens={usage.completion_tokens if usage else 'N/A'})"
                )
            raise RuntimeError(
                f"OpenAI returned empty content "
                f"(finish_reason={finish_reason}, "
                f"prompt_tokens={usage.prompt_tokens if usage else 'N/A'}, "
                f"completion_tokens={usage.completion_tokens if usage else 'N/A'})"
            )
        if finish_reason == "length":
            self.logger.warning(
                "OpenAI response was truncated (finish_reason=length); returning partial content. "
                "Consider increasing max_tokens_per_summary in config.yaml."
            )
        return text
```

**Step 4: Add `reasoning_effort` parameter to `OllamaProvider.chat_completion` (line 133)**

Change:
```python
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
```
to:
```python
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None = None,  # noqa: ARG002 — accepted, not used by Ollama
    ) -> str:
```

**Step 5: Add `reasoning_effort` parameter to `AnthropicProvider.chat_completion` (line 214)**

Change:
```python
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
```
to:
```python
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: str | None = None,  # noqa: ARG002 — accepted, not used by Anthropic
    ) -> str:
```

**Step 6: Run tests for ai_providers**

```
make test-fast 2>&1 | grep -E "(PASSED|FAILED|ERROR|test_openai_provider.*reasoning|test_anthropic.*reasoning|test_ollama.*reasoning)"
```

Expected: all five new provider tests PASS. All existing provider tests still PASS.

**Step 7: Run lint**

```
make lint
```

Fix any issues before continuing.

**Step 8: Commit**

```bash
git add src/ai_providers.py
git commit -m "feat: add reasoning_effort param to chat_completion; OpenAI passes it and falls back on BadRequestError"
```

---

### Task 4: Implement `reasoning_effort="low"` in `src/summarizer.py` retry

**Files:**
- Modify: `src/summarizer.py`

**Step 1: In `_summarize_channel`, update the retry call to pass `reasoning_effort="low"` (around line 211)**

Find:
```python
                summary = await self.provider.chat_completion(
                    messages=chat_messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=retry_max_tokens,
                )
```

Replace with:
```python
                summary = await self.provider.chat_completion(
                    messages=chat_messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=retry_max_tokens,
                    reasoning_effort="low",
                )
```

**Step 2: Run the summarizer tests**

```
make test-fast 2>&1 | grep -E "(PASSED|FAILED|ERROR|test_summarize_channel.*retry|test_summarize_channel.*reasoning)"
```

Expected: all summarizer retry tests PASS. No regressions.

**Step 3: Run the full test suite**

```
make test
```

Expected: all tests PASS with coverage ≥ existing baseline (49%+).

**Step 4: Run lint**

```
make lint
```

Fix any issues.

**Step 5: Commit**

```bash
git add src/summarizer.py
git commit -m "feat: pass reasoning_effort=low on retry to suppress reasoning-model overhead"
```

---

### Task 5: Verify acceptance criteria

- [ ] `make test` passes — all tests green, coverage ≥ existing baseline
- [ ] `make lint` passes — no lint errors
- [ ] The three new OpenAI provider tests pass (reasoning_effort passed, omitted when None, fallback on BadRequestError)
- [ ] The two new provider tests pass (Anthropic and Ollama accept the param)
- [ ] The updated and new summarizer retry tests pass (reasoning_effort="low" on retry)
- [ ] No existing tests regressed

---

## Post-Completion

**Manual verification:**

Run a real digest with a high-traffic channel using `gpt-5-nano` (or whichever model was failing) and confirm:
- No more "Token budget exhausted … retry also failed" in the logs
- Summary is generated successfully
- If model supports reasoning_effort: the retry succeeds on the first attempt
- If model does not support reasoning_effort: a DEBUG log appears ("reasoning_effort=low rejected by model, retrying without it") and the plain retry succeeds or fails as before

*Note: ralphex automatically moves completed plans to `docs/plans/completed/`*
