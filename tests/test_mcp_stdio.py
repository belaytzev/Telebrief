"""End-to-end check of `python main.py mcp`: the stdio server answers introspection."""

import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MAIN = Path(__file__).resolve().parent.parent / "main.py"
CONFIG = """
channels:
  - id: "@example"
    name: "Example"
settings:
  target_user_id: 1
"""
DUMMY_ENV = {
    "TELEGRAM_API_ID": "1",
    "TELEGRAM_API_HASH": "dummy",
    "TELEGRAM_BOT_TOKEN": "1:dummy",
    "OPENAI_API_KEY": "sk-dummy",
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_stdio_lists_tools_without_telegram(tmp_path):
    (tmp_path / "config.yaml").write_text(CONFIG)
    params = StdioServerParameters(
        command=sys.executable, args=[str(MAIN), "mcp"], cwd=str(tmp_path), env=DUMMY_ENV
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    assert {t.name for t in tools.tools} == {
        "get_digest",
        "get_last_digest",
        "get_channel_messages",
        "search_messages",
    }
