"""Escape XML-style delimiters in untrusted content to prevent prompt injection breakout."""

import re


def escape_xml_delimiters(text: str) -> str:
    """Escape opening and closing XML tags that match our prompt delimiters.

    Prevents untrusted content from breaking out of XML-delimited data
    sections (e.g. <channel_messages>, </channel_summary>) in AI prompts.

    Only escapes our specific delimiter tags, not arbitrary XML, to minimize
    interference with normal message content.
    """
    text = re.sub(
        r"</?(channel_messages|channel_summary)\b[^>]*>",
        lambda m: m.group(0).replace("<", "&lt;").replace(">", "&gt;"),
        text,
        flags=re.IGNORECASE,
    )
    return text
