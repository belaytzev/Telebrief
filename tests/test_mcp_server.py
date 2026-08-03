"""Tests for the MCP server module."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from src.mcp_server import _is_loopback, build_server


def _text(result) -> str:
    """Extract the text payload from a CallToolResult."""
    return result.content[0].text


@pytest.fixture
def server(sample_config, mock_logger):
    return build_server(sample_config, mock_logger)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_registers_both_tools(server):
    """Both digest tools are exposed with a description for the model."""
    tools = await server.list_tools()

    names = {tool.name for tool in tools}
    assert names == {"get_digest", "get_last_digest"}
    assert all(tool.description for tool in tools)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_digest_returns_built_digest(server, sample_config, mock_logger):
    """get_digest passes the lookback window through and returns the digest text."""
    with patch("src.mcp_server.build_digest", new_callable=AsyncMock) as mock_build:
        mock_build.return_value = "Header\n\nGroup msg"

        result = await server.call_tool("get_digest", {"hours": 12})

        assert _text(result) == "Header\n\nGroup msg"
        mock_build.assert_called_once_with(sample_config, mock_logger, 12)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_digest_defaults_to_24_hours(server, sample_config, mock_logger):
    """Calling get_digest without arguments uses a 24 hour window."""
    with patch("src.mcp_server.build_digest", new_callable=AsyncMock) as mock_build:
        mock_build.return_value = "digest"

        await server.call_tool("get_digest", {})

        mock_build.assert_called_once_with(sample_config, mock_logger, 24)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_digest_reports_empty_result(server):
    """An empty build reads as an explicit 'nothing found', not a blank response."""
    with patch("src.mcp_server.build_digest", new_callable=AsyncMock) as mock_build:
        mock_build.return_value = ""

        result = await server.call_tool("get_digest", {"hours": 6})

        assert "No messages found" in _text(result)
        assert "6 hours" in _text(result)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("hours", [0, -5, 169, 100000])
async def test_get_digest_rejects_out_of_range_hours(server, hours):
    """Out-of-range windows fail before any collection happens."""
    with patch("src.mcp_server.build_digest", new_callable=AsyncMock) as mock_build:
        with pytest.raises(ToolError):
            await server.call_tool("get_digest", {"hours": hours})

        mock_build.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_last_digest_without_cache(server):
    """With no cached digest the tool points the model at get_digest."""
    with patch("src.mcp_server.read_last_digest", return_value=None):
        result = await server.call_tool("get_last_digest", {})

        assert "get_digest" in _text(result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_last_digest_includes_age(server):
    """A cached digest is returned together with when it was generated."""
    cached = {
        "generated_at": "2026-08-03T09:00:12+00:00",
        "hours": 24,
        "text": "Header\n\nGroup msg",
    }
    with patch("src.mcp_server.read_last_digest", return_value=cached):
        result = await server.call_tool("get_last_digest", {})

        text = _text(result)
        assert "Header\n\nGroup msg" in text
        assert "2026-08-03T09:00:12+00:00" in text
        assert "24" in text


@pytest.mark.unit
@pytest.mark.parametrize(
    "host,expected",
    [
        ("127.0.0.1", True),
        ("localhost", True),
        ("::1", True),
        ("0.0.0.0", False),
        ("192.168.1.10", False),
        ("telebrief.local", False),
    ],
)
def test_is_loopback(host, expected):
    """Only addresses that keep the port on this machine count as loopback."""
    assert _is_loopback(host) is expected


@pytest.mark.unit
def test_warns_when_bound_to_public_interface(sample_config, mock_logger):
    """Binding beyond loopback warns, since the server has no authentication."""
    sample_config.mcp.host = "0.0.0.0"

    build_server(sample_config, mock_logger)

    mock_logger.warning.assert_called_once()
    assert "authentication" in mock_logger.warning.call_args[0][0]


@pytest.mark.unit
def test_no_warning_on_loopback(sample_config, mock_logger):
    """The default loopback bind is silent."""
    sample_config.mcp.host = "127.0.0.1"

    build_server(sample_config, mock_logger)

    mock_logger.warning.assert_not_called()
