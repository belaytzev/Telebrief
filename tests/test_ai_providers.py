"""Tests for ai_providers module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai_providers import (  # isort: skip
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openai_provider_empty_content(mock_logger):
    """Test OpenAI provider with empty content response."""
    with patch("src.ai_providers.AsyncOpenAI"):
        provider = OpenAIProvider(api_key="sk-test", logger=mock_logger)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        provider.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await provider.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-5-nano",
            temperature=0.7,
            max_tokens=500,
        )

        assert result == ""


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
    assert len(debug_calls) == 2

    # First call: request log
    assert "Ollama request" in debug_calls[0][0][0]
    assert debug_calls[0][0][1] == "http://localhost:11434/api/chat"
    assert debug_calls[0][0][2] == "llama3"

    # Second call: response log
    assert "Ollama response" in debug_calls[1][0][0]
    assert debug_calls[1][0][1] == 200
    assert debug_calls[1][0][2] == 42


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


# --- Helper for async context managers ---


class AsyncContextManager:
    """Helper to mock async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
