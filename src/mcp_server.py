"""MCP server exposing Telebrief digests to MCP clients.

Runs inside the main Telebrief process so that digest generation reuses the same
Telegram session, configuration and lock as the scheduler and the bot.
"""

from __future__ import annotations

import ipaddress
import logging

from mcp.server import MCPServer

from src.collector import Message
from src.config_loader import Config
from src.core import (
    MAX_CHANNEL_MESSAGES,
    MAX_DIGEST_HOURS,
    build_digest,
    collect_channel_messages,
    read_last_digest,
    search_messages,
    validate_hours,
)


def _is_loopback(host: str) -> bool:
    """Whether host keeps the server reachable only from this machine."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _format_messages(channel: str, messages: list[Message], source: str, hours: int) -> str:
    """Render collected messages as the flat text the model reads."""
    header = f"channel: {channel} (from {source}, {len(messages)} msgs, last {hours}h)"
    body = "\n\n".join(
        f"[{msg.timestamp.isoformat()}] {msg.sender}\n{msg.text}\n{msg.link}" for msg in messages
    )
    return f"{header}\n\n{body}"


def _format_search(query: str, messages: list[Message], failed: list[str], days: int) -> str:
    """Render search matches newest first, each tagged with its channel."""
    header = f"search: {query!r} ({len(messages)} matches, last {days} days)"
    if failed:
        header += f"\nsearch failed in: {', '.join(failed)}"
    if not messages:
        return f"{header}\n\nNo matches."
    body = "\n\n".join(
        f"[{msg.timestamp.isoformat()}] {msg.channel_name} · {msg.sender}\n{msg.text}\n{msg.link}"
        for msg in messages
    )
    return f"{header}\n\n{body}"


def build_server(config: Config, logger: logging.Logger) -> MCPServer:
    """Build the MCP server exposing the digest tools.

    Args:
        config: Application configuration
        logger: Logger instance

    Returns:
        Configured MCPServer, not yet running
    """
    if not _is_loopback(config.mcp.host):
        logger.warning(
            f"MCP server binds to {config.mcp.host!r}, which is reachable from the network. "
            "It has no authentication — anyone who can reach this port can trigger digest "
            "generation and read your channels. Bind 127.0.0.1 or firewall the port."
        )

    mcp = MCPServer("telebrief")

    @mcp.tool()
    async def get_digest(hours: int = 24) -> str:
        """Generate a fresh digest of the configured Telegram channels.

        Collects messages, summarizes them with AI and formats the result exactly
        as the digest delivered to Telegram. Takes roughly 20-90 seconds and costs
        AI provider tokens, so prefer get_last_digest when recent data is enough.
        Use hours=168 for a weekly digest.

        Args:
            hours: How many hours back to look, 1 to 168 (default 24)
        """
        validate_hours(hours)
        digest = await build_digest(config, logger, hours)
        return digest or f"No messages found in the last {hours} hours."

    @mcp.tool()
    async def get_last_digest() -> str:
        """Return the most recently generated digest without regenerating it.

        Instant and free. The digest may be stale — its generation time is included
        in the response, so check whether it is recent enough before relying on it.
        """
        cached = read_last_digest()
        if cached is None:
            return "No digest has been generated yet. Use get_digest to build one."
        return (
            f"Digest generated at {cached.get('generated_at', 'unknown time')} "
            f"covering the previous {cached.get('hours', '?')} hours:\n\n{cached['text']}"
        )

    @mcp.tool()
    async def get_channel_messages(channel: str, hours: int = 24, limit: int = 200) -> str:
        """Return the individual messages of one configured channel, unsummarized.

        Reads from Telebrief's message store when it holds the requested window, and
        falls back to a live Telegram read otherwise. Free and instant on the stored
        path; the fallback takes a few seconds. The response header says which was used.

        Args:
            channel: Channel name or id as configured under channels[*] in config.yaml
            hours: How many hours back to look, 1 to 168 (default 24)
            limit: Maximum messages to return, 1 to 500, newest kept (default 200)
        """
        messages, source = await collect_channel_messages(config, logger, channel, hours, limit)
        if not messages:
            return f"No messages in {channel!r} in the last {hours} hours."
        return _format_messages(channel, messages, source, hours)

    @mcp.tool(name="search_messages")
    async def search_messages_tool(
        query: str, channel: str | None = None, days: int = 30, limit: int = 30
    ) -> str:
        """Find messages mentioning something across the configured Telegram channels.

        Uses Telegram's own search, so it covers each channel's full history, not only
        what digests collected, and it matches words, not substrings or regexes. No AI
        tokens spent. Makes one Telegram request per channel: pass channel when you
        know where to look. Channel filters from config.yaml are not applied.

        Args:
            query: Words to search for
            channel: Channel name or id as configured under channels[*]; all channels if omitted
            days: How many days back to search, 1 to 365 (default 30)
            limit: Maximum matches to return, 1 to 100, newest kept (default 30)
        """
        messages, failed = await search_messages(
            config, logger, query, channel=channel, days=days, limit=limit
        )
        return _format_search(query, messages, failed, days)

    logger.info(
        f"MCP tools registered: get_digest (max {MAX_DIGEST_HOURS}h), get_last_digest, "
        f"get_channel_messages (max {MAX_CHANNEL_MESSAGES} msgs), search_messages"
    )
    return mcp
