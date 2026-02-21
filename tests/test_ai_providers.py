"""Tests for ai_providers module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai_providers import (  # isort: skip
    _redact_url,
    AnthropicProvider,
    create_provider,
    OllamaProvider,
    OpenAIProvider,
)

# --- Factory tests ---


@pytest.mark.unit
def test_create_provider_openai(mock_logger):
    """Test creating OpenAI provider."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = create_provider(
            provider_name="openai",
            logger=mock_logger,
            openai_api_key="sk-test",
        )
        assert isinstance(provider, OpenAIProvider)


@pytest.mark.unit
def test_create_provider_ollama(mock_logger):
    """Test creating Ollama provider."""
    provider = create_provider(
        provider_name="ollama",
        logger=mock_logger,
        ollama_base_url="http://localhost:11434",
    )
    assert isinstance(provider, OllamaProvider)


@pytest.mark.unit
def test_create_provider_anthropic(mock_logger):
    """Test creating Anthropic provider."""
    provider = create_provider(
        provider_name="anthropic",
        logger=mock_logger,
        anthropic_api_key="sk-ant-test",
    )
    assert isinstance(provider, AnthropicProvider)


@pytest.mark.unit
def test_create_provider_unknown(mock_logger):
    """Test error for unknown provider."""
    with pytest.raises(ValueError, match="Unknown AI provider"):
        create_provider(provider_name="unknown", logger=mock_logger)


@pytest.mark.unit
def test_create_provider_openai_missing_key(mock_logger):
    """Test error when OpenAI key is missing."""
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        create_provider(provider_name="openai", logger=mock_logger, openai_api_key="")


@pytest.mark.unit
def test_create_provider_anthropic_missing_key(mock_logger):
    """Test error when Anthropic key is missing."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        create_provider(provider_name="anthropic", logger=mock_logger, anthropic_api_key="")


@pytest.mark.unit
def test_create_provider_case_insensitive(mock_logger):
    """Test that provider name is case-insensitive."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = create_provider(
            provider_name="OpenAI",
            logger=mock_logger,
            openai_api_key="sk-test",
        )
        assert isinstance(provider, OpenAIProvider)


# --- OpenAI provider tests ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_chat_completion(mock_logger):
    """Test OpenAI provider chat completion."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=500,
        )

        assert result == "Test response"
        # Verify max_completion_tokens is used instead of max_tokens
        call_kwargs = provider.client.chat.completions.create.call_args[1]
        assert "max_completion_tokens" in call_kwargs
        assert "max_tokens" not in call_kwargs
        assert call_kwargs["max_completion_tokens"] == 500


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_none_content_raises(mock_logger):
    """Test OpenAI provider raises RuntimeError when content is None."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_choice.message.refusal = None
        mock_choice.finish_reason = "length"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 1234
        mock_response.usage.completion_tokens = 0
        mock_response.usage.total_tokens = 1234
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(RuntimeError, match="empty content"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-5-nano",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_empty_string_content_raises(mock_logger):
    """Test OpenAI provider raises RuntimeError when content is empty string."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_choice = MagicMock()
        mock_choice.message.content = "   "
        mock_choice.message.refusal = None
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 1
        mock_response.usage.total_tokens = 101
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(RuntimeError, match="empty content"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-5-nano",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_refusal_raises(mock_logger):
    """Test OpenAI provider raises RuntimeError when model refuses."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_choice.message.refusal = "I cannot process this request"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 10
        mock_response.usage.total_tokens = 110
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        with pytest.raises(RuntimeError, match="empty content"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-5-nano",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_logs_response_metadata(mock_logger):
    """Test OpenAI provider logs finish_reason and token usage."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_choice = MagicMock()
        mock_choice.message.content = "Valid response"
        mock_choice.message.refusal = None
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 600
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=500,
        )

        assert result == "Valid response"

        # Verify debug logging was called with response metadata
        debug_messages = [str(call) for call in mock_logger.debug.call_args_list]
        debug_text = " ".join(debug_messages)
        assert "finish_reason" in debug_text
        assert "stop" in debug_text
        assert "prompt_tokens" in debug_text


# --- Ollama provider tests ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_chat_completion(mock_logger):
    """Test Ollama provider chat completion."""
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"message": {"content": "Ollama response"}})

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="llama3",
            temperature=0.7,
            max_tokens=500,
        )

    assert result == "Ollama response"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_error(mock_logger):
    """Test Ollama provider error handling."""
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError, match="Ollama API error 500"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="llama3",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_error_body_truncated(mock_logger):
    """Test that long error bodies are truncated in the exception message."""
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    long_body = "x" * 500
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value=long_body)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError) as exc_info:
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="llama3",
                temperature=0.7,
                max_tokens=500,
            )

    # Error message should contain at most 200 chars of the body
    error_msg = str(exc_info.value)
    assert "Ollama API error 500" in error_msg
    assert len(error_msg) < 250  # status prefix + 200 chars of body


@pytest.mark.unit
def test_ollama_provider_url_trailing_slash(mock_logger):
    """Test Ollama provider strips trailing slash from URL."""
    provider = OllamaProvider(base_url="http://localhost:11434/", logger=mock_logger)
    assert provider.base_url == "http://localhost:11434"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_ndjson_content_type(mock_logger):
    """Test Ollama provider handles application/x-ndjson content type.

    Ollama returns application/x-ndjson even with stream: false.
    aiohttp's resp.json() rejects non-application/json by default.
    """
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    response_data = {"message": {"content": "Ollama ndjson response"}}

    mock_response = MagicMock()
    mock_response.status = 200
    # Simulate the real behavior: json() with strict content_type raises ContentTypeError
    # when Content-Type is application/x-ndjson
    mock_response.headers = {"Content-Type": "application/x-ndjson"}
    mock_response.json = AsyncMock(return_value=response_data)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="llama3",
            temperature=0.7,
            max_tokens=500,
        )

    assert result == "Ollama ndjson response"
    # Verify json() was called with content_type=None to bypass strict checking
    mock_response.json.assert_called_once_with(content_type=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_debug_logging(mock_logger):
    """Test that OllamaProvider emits debug logs before and after the HTTP call."""
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content_length = 42
    mock_response.json = AsyncMock(return_value={"message": {"content": "ok"}})

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="llama3",
            temperature=0.7,
            max_tokens=500,
        )

    debug_calls = [call for call in mock_logger.debug.call_args_list]
    assert len(debug_calls) == 3

    # First call: request log
    assert "Ollama request" in debug_calls[0][0][0]
    assert debug_calls[0][0][1] == "http://localhost:11434/api/chat"
    assert debug_calls[0][0][2] == "llama3"

    # Second call: response log
    assert "Ollama response" in debug_calls[1][0][0]
    assert debug_calls[1][0][1] == 200
    assert debug_calls[1][0][2] == 42

    # Third call: metadata log
    assert "Ollama metadata" in debug_calls[2][0][0]


@pytest.mark.unit
def test_ollama_provider_minimum_timeout(mock_logger):
    """Test that Ollama provider gets at least 120s timeout even when lower value is configured."""
    provider = create_provider(
        provider_name="ollama",
        logger=mock_logger,
        ollama_base_url="http://localhost:11434",
        api_timeout=30,
    )
    assert isinstance(provider, OllamaProvider)
    assert provider.timeout.total >= 120


@pytest.mark.unit
def test_ollama_provider_respects_higher_timeout(mock_logger):
    """Test that Ollama provider uses the configured timeout when it exceeds the minimum."""
    provider = create_provider(
        provider_name="ollama",
        logger=mock_logger,
        ollama_base_url="http://localhost:11434",
        api_timeout=300,
    )
    assert isinstance(provider, OllamaProvider)
    assert provider.timeout.total == 300


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_empty_content_raises(mock_logger):
    """Test Ollama provider raises RuntimeError when content is empty."""
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content_length = 42
    mock_response.json = AsyncMock(
        return_value={
            "message": {"content": ""},
            "model": "llama3",
            "eval_count": 0,
            "prompt_eval_count": 100,
        }
    )

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError, match="empty content"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="llama3",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ollama_provider_missing_message_key_raises(mock_logger):
    """Test Ollama provider raises RuntimeError when message key is missing."""
    provider = OllamaProvider(base_url="http://localhost:11434", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.content_length = 10
    mock_response.json = AsyncMock(
        return_value={
            "model": "llama3",
            "eval_count": 0,
            "prompt_eval_count": 50,
        }
    )

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError, match="empty content"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="llama3",
                temperature=0.7,
                max_tokens=500,
            )


# --- Anthropic provider tests ---


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anthropic_provider_chat_completion(mock_logger):
    """Test Anthropic provider chat completion."""
    provider = AnthropicProvider(api_key="sk-ant-test", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"content": [{"type": "text", "text": "Anthropic response"}]}
    )

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        result = await provider.chat_completion(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ],
            model="claude-sonnet-4-5-20250929",
            temperature=0.7,
            max_tokens=500,
        )

    assert result == "Anthropic response"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anthropic_provider_error_body_truncated(mock_logger):
    """Test that long Anthropic error bodies are truncated in the exception message."""
    provider = AnthropicProvider(api_key="sk-ant-test", logger=mock_logger)

    long_body = "y" * 500
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value=long_body)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError) as exc_info:
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4-5-20250929",
                temperature=0.7,
                max_tokens=500,
            )

    error_msg = str(exc_info.value)
    assert "Anthropic API error 500" in error_msg
    assert len(error_msg) < 250


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anthropic_provider_error(mock_logger):
    """Test Anthropic provider error handling."""
    provider = AnthropicProvider(api_key="sk-ant-test", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.text = AsyncMock(return_value="Unauthorized")

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError, match="Anthropic API error 401"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4-5-20250929",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anthropic_provider_empty_content_array_raises(mock_logger):
    """Test Anthropic provider raises RuntimeError when content array is empty."""
    provider = AnthropicProvider(api_key="sk-ant-test", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "content": [],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 500, "output_tokens": 0},
        }
    )

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError, match="empty content"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4-5-20250929",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anthropic_provider_no_text_blocks_raises(mock_logger):
    """Test Anthropic provider raises RuntimeError when content has no text blocks."""
    provider = AnthropicProvider(api_key="sk-ant-test", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "content": [{"type": "tool_use", "id": "123", "name": "test"}],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 200, "output_tokens": 50},
        }
    )

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        with pytest.raises(RuntimeError, match="empty content"):
            await provider.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="claude-sonnet-4-5-20250929",
                temperature=0.7,
                max_tokens=500,
            )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_anthropic_provider_logs_response_metadata(mock_logger):
    """Test Anthropic provider logs stop_reason and usage."""
    provider = AnthropicProvider(api_key="sk-ant-test", logger=mock_logger)

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "content": [{"type": "text", "text": "Valid response"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 300, "output_tokens": 75},
        }
    )

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=AsyncContextManager(mock_response))
    mock_session.close = AsyncMock()

    with patch("src.ai_providers.aiohttp.ClientSession") as mock_cs:
        mock_cs.return_value = AsyncContextManager(mock_session)
        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-sonnet-4-5-20250929",
            temperature=0.7,
            max_tokens=500,
        )

    assert result == "Valid response"

    debug_messages = [str(call) for call in mock_logger.debug.call_args_list]
    debug_text = " ".join(debug_messages)
    assert "stop_reason" in debug_text
    assert "end_turn" in debug_text
    assert "input_tokens" in debug_text


# --- URL redaction tests ---


@pytest.mark.unit
def test_redact_url_no_credentials():
    """Test that URLs without credentials are returned unchanged."""
    url = "http://localhost:11434/api/chat"
    assert _redact_url(url) == url


@pytest.mark.unit
def test_redact_url_with_credentials():
    """Test that URLs with embedded credentials are redacted."""
    url = "http://user:secret@myhost:11434/api/chat"
    redacted = _redact_url(url)
    assert "user" not in redacted
    assert "secret" not in redacted
    assert "myhost" in redacted
    assert "11434" in redacted
    assert "***@" in redacted


@pytest.mark.unit
def test_redact_url_with_username_only():
    """Test that URLs with only a username are redacted."""
    url = "http://admin@myhost:11434/api/chat"
    redacted = _redact_url(url)
    assert "admin" not in redacted
    assert "***@" in redacted


# --- Helper for async context managers ---


class AsyncContextManager:
    """Helper to mock async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
