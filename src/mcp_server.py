"""MCP server exposing Telebrief digests to MCP clients.

Runs inside the main Telebrief process so that digest generation reuses the same
Telegram session, configuration and lock as the scheduler and the bot.
"""

from __future__ import annotations

import ipaddress
import logging

from mcp.server import MCPServer

from src.config_loader import Config
from src.core import MAX_DIGEST_HOURS, build_digest, read_last_digest, validate_hours


def _is_loopback(host: str) -> bool:
    """Whether host keeps the server reachable only from this machine."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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

    logger.info(f"MCP tools registered: get_digest (max {MAX_DIGEST_HOURS}h), get_last_digest")
    return mcp
