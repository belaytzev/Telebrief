"""Tests for the DigestGrouper module."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.config_loader import DigestGroupConfig
from src.grouper import DigestGrouper


@pytest.fixture
def config_with_groups(sample_config):
    """Config with digest groups configured."""
    sample_config.settings.digest_mode = "digest"
    sample_config.settings.digest_groups = [
        DigestGroupConfig(name="Events", description="Conferences, meetups, launches"),
        DigestGroupConfig(name="News", description="Politics, economy, world affairs"),
    ]
    return sample_config


@pytest.fixture
def config_with_other_group(sample_config):
    """Config where user explicitly defines an 'Other' group."""
    sample_config.settings.digest_mode = "digest"
    sample_config.settings.output_language = "English"
    sample_config.settings.digest_groups = [
        DigestGroupConfig(name="News", description="Breaking news"),
        DigestGroupConfig(name="Other", description="Miscellaneous stuff"),
    ]
    return sample_config


@pytest.fixture
def grouper(config_with_groups, mock_logger):
    """Create a DigestGrouper with mocked AI provider."""
    with patch("src.grouper.create_provider") as mock_create:
        mock_provider = AsyncMock()
        mock_create.return_value = mock_provider
        g = DigestGrouper(config_with_groups, mock_logger)
        g.provider = mock_provider
        return g


@pytest.fixture
def grouper_english(config_with_other_group, mock_logger):
    """Create a DigestGrouper with English config and mocked AI provider."""
    with patch("src.grouper.create_provider") as mock_create:
        mock_provider = AsyncMock()
        mock_create.return_value = mock_provider
        g = DigestGrouper(config_with_other_group, mock_logger)
        g.provider = mock_provider
        return g


class TestBuildGroupDefinitions:
    """Tests for _build_group_definitions()."""

    def test_adds_implicit_other_when_not_in_config(self, grouper):
        """Other group is added when not user-defined."""
        groups = grouper._build_group_definitions()
        group_names = [g.name for g in groups]
        # Config has Events, News; Other should be appended
        assert len(groups) == 3
        assert "Events" in group_names
        assert "News" in group_names
        # The implicit Other uses the localized name (Russian: "Другое")
        assert groups[-1].name == "Другое"

    def test_does_not_duplicate_other_when_in_config(self, grouper_english):
        """Other group is NOT duplicated when already user-defined."""
        groups = grouper_english._build_group_definitions()
        group_names = [g.name for g in groups]
        # Should have exactly News and Other, no duplicate
        assert group_names.count("Other") == 1
        assert len(groups) == 2


class TestParseGroupedResponse:
    """Tests for _parse_grouped_response()."""

    def test_valid_json_returns_correct_dict(self, grouper):
        """Valid JSON response is parsed into GroupedPoint objects."""
        response = json.dumps({
            "Events": [
                {"point": "Conference on AI", "source": "TechNews"},
                {"point": "Product launch", "source": "Startups"},
            ],
            "News": [
                {"point": "Election results", "source": "Politics"},
            ],
        })
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert "Events" in result
        assert len(result["Events"]) == 2
        assert result["Events"][0].point == "Conference on AI"
        assert result["Events"][0].source == "TechNews"
        assert "News" in result
        assert len(result["News"]) == 1

    def test_json_with_markdown_fences_parses_correctly(self, grouper):
        """JSON wrapped in markdown code fences is parsed correctly."""
        inner = json.dumps({
            "Events": [{"point": "Meetup tonight", "source": "Local"}],
        })
        response = f"```json\n{inner}\n```"
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert "Events" in result
        assert result["Events"][0].point == "Meetup tonight"

    def test_invalid_json_returns_empty_dict(self, grouper):
        """Invalid JSON returns empty dict instead of exposing raw AI response."""
        response = "This is not JSON at all"
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert result == {}

    def test_empty_invalid_json_returns_empty_dict(self, grouper):
        """Empty/whitespace-only invalid response returns empty dict."""
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response("   ", valid_names)

        assert result == {}

    def test_case_insensitive_group_matching(self, grouper):
        """AI-returned group names are matched case-insensitively."""
        response = json.dumps({
            "events": [{"point": "Lowercase match", "source": "Ch1"}],
            "NEWS": [{"point": "Uppercase match", "source": "Ch2"}],
        })
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert "Events" in result
        assert result["Events"][0].point == "Lowercase match"
        assert "News" in result
        assert result["News"][0].point == "Uppercase match"

    def test_empty_groups_excluded(self, grouper):
        """Groups with no valid points are not included in result."""
        response = json.dumps({
            "Events": [{"point": "Something", "source": "Ch1"}],
            "News": [],  # empty list
        })
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert "Events" in result
        assert "News" not in result


@pytest.mark.asyncio
class TestGroupSummaries:
    """Tests for group_summaries() end-to-end with mocked AI provider."""

    async def test_end_to_end_with_mocked_provider(self, grouper):
        """group_summaries calls AI provider and returns parsed groups."""
        ai_response = json.dumps({
            "Events": [
                {"point": "AI Summit 2026", "source": "TechChannel"},
            ],
            "News": [
                {"point": "Market update", "source": "FinanceChannel"},
            ],
        })
        grouper.provider.chat_completion.return_value = ai_response

        channel_summaries = {
            "TechChannel": "Summary about AI Summit 2026",
            "FinanceChannel": "Summary about market update",
        }

        result = await grouper.group_summaries(channel_summaries)

        # Verify AI was called
        grouper.provider.chat_completion.assert_called_once()
        call_kwargs = grouper.provider.chat_completion.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # Verify result
        assert "Events" in result
        assert result["Events"][0].point == "AI Summit 2026"
        assert "News" in result
        assert result["News"][0].point == "Market update"

    async def test_empty_channel_summaries_returns_empty(self, grouper):
        """Empty input returns empty dict without calling AI."""
        result = await grouper.group_summaries({})
        assert result == {}
        grouper.provider.chat_completion.assert_not_called()

    async def test_ai_error_propagates(self, grouper):
        """AI provider errors propagate to caller."""
        grouper.provider.chat_completion.side_effect = RuntimeError("API down")

        with pytest.raises(RuntimeError, match="API down"):
            await grouper.group_summaries({"ch": "summary"})
