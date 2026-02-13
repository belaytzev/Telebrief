"""
AI provider abstraction for multiple LLM backends.

Supports OpenAI, Ollama, and Anthropic providers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import aiohttp
import httpx
from openai import AsyncOpenAI


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        Generate a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Generated text content
        """


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, logger: logging.Logger, timeout: int = 60):
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(timeout, connect=min(10.0, float(timeout))),
        )
        self.logger = logger

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""


class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""

    def __init__(self, base_url: str, logger: logging.Logger, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.logger = logger
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"Ollama API error {resp.status}: {body}")
                data = await resp.json()

        content: str = data.get("message", {}).get("content", "")
        return content.strip()


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, logger: logging.Logger, timeout: int = 60):
        self.api_key = api_key
        self.logger = logger
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        # Extract system message and user messages
        system_text = ""
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                api_messages.append(msg)

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": api_messages,
        }
        if system_text:
            payload["system"] = system_text
        payload["temperature"] = temperature

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"Anthropic API error {resp.status}: {body}")
                data = await resp.json()

        content_blocks = data.get("content", [])
        texts = [block["text"] for block in content_blocks if block.get("type") == "text"]
        return "\n".join(texts).strip()


def create_provider(
    provider_name: str,
    logger: logging.Logger,
    *,
    openai_api_key: str = "",
    anthropic_api_key: str = "",
    ollama_base_url: str = "http://localhost:11434",
    api_timeout: int = 60,
) -> AIProvider:
    """
    Factory function to create an AI provider.

    Args:
        provider_name: One of 'openai', 'ollama', 'anthropic'
        logger: Logger instance
        openai_api_key: OpenAI API key (required for 'openai' provider)
        anthropic_api_key: Anthropic API key (required for 'anthropic' provider)
        ollama_base_url: Ollama server URL (for 'ollama' provider)
        api_timeout: HTTP request timeout in seconds

    Returns:
        AIProvider instance

    Raises:
        ValueError: If provider_name is unknown or required keys are missing
    """
    name = provider_name.lower()

    if name == "openai":
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        return OpenAIProvider(api_key=openai_api_key, logger=logger, timeout=api_timeout)

    if name == "ollama":
        return OllamaProvider(base_url=ollama_base_url, logger=logger, timeout=api_timeout)

    if name == "anthropic":
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        return AnthropicProvider(api_key=anthropic_api_key, logger=logger, timeout=api_timeout)

    raise ValueError(
        f"Unknown AI provider: '{provider_name}'. "
        f"Supported providers: openai, ollama, anthropic"
    )
