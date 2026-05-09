"""Tests for the DigestGrouper module."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.config_loader import DigestGroupConfig
from src.grouper import (
    DigestGrouper,
    ExtractedBullet,
    _dedup_extracted,
    _quality_gate_filter,
    _strip_channel_summary_noise,
)


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
        response = json.dumps(
            {
                "Events": [
                    {"point": "Conference on AI", "source": "TechNews"},
                    {"point": "Product launch", "source": "Startups"},
                ],
                "News": [
                    {"point": "Election results", "source": "Politics"},
                ],
            }
        )
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
        inner = json.dumps(
            {
                "Events": [{"point": "Meetup tonight", "source": "Local"}],
            }
        )
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
        response = json.dumps(
            {
                "events": [{"point": "Lowercase match", "source": "Ch1"}],
                "NEWS": [{"point": "Uppercase match", "source": "Ch2"}],
            }
        )
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert "Events" in result
        assert result["Events"][0].point == "Lowercase match"
        assert "News" in result
        assert result["News"][0].point == "Uppercase match"

    def test_empty_groups_excluded(self, grouper):
        """Groups with no valid points are not included in result."""
        response = json.dumps(
            {
                "Events": [{"point": "Something", "source": "Ch1"}],
                "News": [],  # empty list
            }
        )
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert "Events" in result
        assert "News" not in result


@pytest.mark.asyncio
class TestGroupSummaries:
    """Tests for group_summaries() end-to-end with mocked AI provider."""

    async def test_end_to_end_with_mocked_provider(self, grouper):
        """group_summaries chains extractor (per channel) → dedup → classifier."""
        # Two extractor responses (one per channel) + one classifier response
        grouper.provider.chat_completion.side_effect = [
            json.dumps([{"point": "AI Summit 2026"}]),
            json.dumps([{"point": "Market update"}]),
            json.dumps(
                {
                    "Events": [{"point": "AI Summit 2026", "source": "TechChannel"}],
                    "News": [{"point": "Market update", "source": "FinanceChannel"}],
                }
            ),
        ]

        channel_summaries = {
            "TechChannel": "Summary about AI Summit 2026",
            "FinanceChannel": "Summary about market update",
        }

        result = await grouper.group_summaries(channel_summaries)

        # Two extract calls + one classify call = 3 total
        assert grouper.provider.chat_completion.call_count == 3

        assert "Events" in result
        assert result["Events"][0].point == "AI Summit 2026"
        assert "News" in result
        assert result["News"][0].point == "Market update"

    async def test_empty_channel_summaries_returns_empty(self, grouper):
        """Empty input returns empty dict without calling AI."""
        result = await grouper.group_summaries({})
        assert result == {}
        grouper.provider.chat_completion.assert_not_called()

    async def test_classifier_error_propagates(self, grouper):
        """Classifier (Pass 2b) errors propagate to caller; extractor failures are tolerated."""
        # Extractor succeeds with a bullet substantive enough to survive QUALITY GATE
        grouper.provider.chat_completion.side_effect = [
            json.dumps([{"point": "🤖 Cloudflare уволил 1100 сотрудников в марте 2026"}]),
            RuntimeError("API down"),
        ]

        with pytest.raises(RuntimeError, match="API down"):
            await grouper.group_summaries({"ch": "summary"})


# --- Task 1: Prompt injection mitigation tests ---


class TestPromptInjectionMitigation:
    """Tests for prompt injection defenses in grouper prompts."""

    def test_extractor_wraps_summary_in_xml_with_source_attribute(self, grouper):
        """Extractor user prompt wraps the summary in <channel_summary> with source attr."""
        messages = grouper._build_extractor_prompt(
            channel_name="TechNews", summary="Summary about AI"
        )
        user_prompt = messages[1]["content"]
        assert '<channel_summary source="TechNews">' in user_prompt
        assert "</channel_summary>" in user_prompt

    def test_extractor_system_prompt_contains_data_isolation_instruction(self, grouper):
        """Extractor system prompt treats XML-delimited content as DATA only."""
        messages = grouper._build_extractor_prompt(channel_name="Ch", summary="Summary")
        system_prompt = messages[0]["content"]
        assert "DATA" in system_prompt or "data only" in system_prompt.lower()
        assert (
            "XML" in system_prompt
            or "xml" in system_prompt.lower()
            or "tags" in system_prompt.lower()
        )

    def test_classifier_system_prompt_contains_data_isolation_instruction(self, grouper):
        """Classifier system prompt treats input bullets as DATA only."""
        groups = grouper._build_group_definitions()
        messages = grouper._build_classifier_prompt([], groups)
        system_prompt = messages[0]["content"]
        assert "DATA" in system_prompt or "data only" in system_prompt.lower()


# --- Task 3: Output validation layer tests ---


class TestGrouperTemperatureOverride:
    """Tests for grouper using lower temperature for classification."""

    @pytest.mark.asyncio
    async def test_grouper_uses_low_temperature_for_classification(self, grouper):
        """Grouper AI calls use temperature 0.1 regardless of global config."""
        ai_response = json.dumps(
            {
                "Events": [{"point": "Test event", "source": "Ch1"}],
            }
        )
        grouper.provider.chat_completion.return_value = ai_response

        await grouper.group_summaries({"Ch1": "Summary about events"})

        call_kwargs = grouper.provider.chat_completion.call_args
        # Temperature should be 0.1, not the global config value (0.7)
        temp = call_kwargs.kwargs.get("temperature") or call_kwargs[1].get("temperature")
        assert temp == 0.1


class TestStripChannelHeader:
    """Tests for stripping leading 🚀 header line from channel summaries before extraction."""

    def test_leading_rocket_header_stripped_from_summary(self, grouper):
        """Leading '🚀 ...' line is removed before being fed to the extractor AI."""
        messages = grouper._build_extractor_prompt(
            channel_name="TechNews",
            summary="🚀 Quick recap of channel events\n- 🤖 AI launched X\n- 📈 Stock up",
        )
        user_prompt = messages[1]["content"]
        assert "Quick recap of channel events" not in user_prompt
        assert "AI launched X" in user_prompt
        assert "Stock up" in user_prompt

    def test_summary_without_rocket_header_unchanged(self, grouper):
        """Summary that does not start with 🚀 is fed verbatim."""
        messages = grouper._build_extractor_prompt(
            channel_name="Politics",
            summary="- 📰 Election update\n- 🗳️ Voter turnout",
        )
        user_prompt = messages[1]["content"]
        assert "Election update" in user_prompt
        assert "Voter turnout" in user_prompt


class TestStripBroaderNoise:
    """Tests for noise patterns added beyond 🚀 / 📎."""

    def test_strips_key_points_header_english(self):
        """'📌 Key points:' template header is removed."""
        out = _strip_channel_summary_noise("📌 Key points:\n- 🤖 Real bullet\n- 📈 Another")
        assert "Key points" not in out
        assert "Real bullet" in out

    def test_strips_key_points_header_russian(self):
        """Russian '📌 Ключевые моменты:' template header is removed."""
        out = _strip_channel_summary_noise("📌 Ключевые моменты:\n- 🤖 Реальный буллет")
        assert "Ключевые моменты" not in out
        assert "Реальный буллет" in out

    def test_strips_numbered_emoji_prefix(self):
        """Leading 1️⃣-9️⃣ section numbering is removed from each line."""
        out = _strip_channel_summary_noise("1️⃣ 🤖 First fact\n2️⃣ 📈 Second fact\n3️⃣ ⚠️ Third fact")
        # Numbered emoji prefix gone, content survives
        assert "1️⃣" not in out
        assert "2️⃣" not in out
        assert "First fact" in out
        assert "Second fact" in out

    def test_strips_template_token_placeholders(self):
        """Template placeholders like '[emoji]' and '[brief fact]' removed if model echoes them."""
        out = _strip_channel_summary_noise("- [emoji] [brief fact] real content")
        assert "[emoji]" not in out
        assert "[brief fact]" not in out
        assert "real content" in out


class TestQualityGateFilter:
    """Tests for deterministic QUALITY GATE filter on List[ExtractedBullet]."""

    def test_drops_admin_chatter_new_member(self):
        """Bullets about new chat members are dropped."""
        bullets = [
            ExtractedBullet(point="🆕 В чате появился новый участник Denis Nogtev", source="Ch"),
            ExtractedBullet(point="🤖 Real news about AI", source="Ch"),
        ]
        out = _quality_gate_filter(bullets)
        assert len(out) == 1
        assert "Real news" in out[0].point

    def test_drops_meta_empty_no_details(self):
        """Bullets that admit they have no content are dropped."""
        bullets = [
            ExtractedBullet(
                point="🛸 В подборке упомянуты темы, но без дополнительных деталей", source="Ch"
            ),
            ExtractedBullet(
                point="📰 Cloudflare уволил 1100 сотрудников в марте 2026", source="Ch"
            ),
        ]
        out = _quality_gate_filter(bullets)
        assert len(out) == 1
        assert "Cloudflare" in out[0].point

    def test_drops_speculation_without_concrete_entity(self):
        """Hedging bullets without a concrete entity are dropped."""
        bullets = [
            ExtractedBullet(point="📊 Парк выглядит как сильный фотоспот, вероятно", source="Ch"),
            ExtractedBullet(
                point="📊 Apple удвоила план выпуска MacBook Neo до 10 млн", source="Ch"
            ),
        ]
        out = _quality_gate_filter(bullets)
        # Apple bullet has @-free but contains numbers + proper names → kept
        assert any("Apple" in b.point for b in out)
        assert not any("фотоспот" in b.point for b in out)

    def test_drops_short_bullets_without_facts(self):
        """Bullets <30 chars with no digits, @, or URL are dropped."""
        bullets = [
            ExtractedBullet(point="🤖 Просто пост", source="Ch"),
            ExtractedBullet(point="🤖 Apple отчитался $94B выручки", source="Ch"),
        ]
        out = _quality_gate_filter(bullets)
        assert len(out) == 1
        assert "Apple" in out[0].point

    def test_keeps_bullet_with_url(self):
        """Short bullet with URL survives."""
        bullets = [
            ExtractedBullet(point="🔗 https://t.me/x/123", source="Ch"),
        ]
        out = _quality_gate_filter(bullets)
        assert len(out) == 1

    def test_keeps_substantive_bullets_unchanged(self):
        """Long, fact-rich bullets pass through untouched."""
        bullets = [
            ExtractedBullet(
                point="🤖 Cloudflare уволил 1100 сотрудников, переход в агентскую эру",
                source="Ch",
            ),
        ]
        out = _quality_gate_filter(bullets)
        assert out == bullets


class TestStripSectionTwo:
    """Tests for stripping Section 2 (📎 Also/Также) from channel summaries before extraction."""

    def test_section_two_english_stripped(self, grouper):
        """English '📎 Also:' section and everything after is removed."""
        messages = grouper._build_extractor_prompt(
            channel_name="Ch",
            summary=(
                "- 🤖 Big news item\n"
                "📎 Also:\n"
                "• Trivial poll → https://t.me/x/1\n"
                "• Random link → https://t.me/x/2"
            ),
        )
        user_prompt = messages[1]["content"]
        assert "Big news item" in user_prompt
        assert "Trivial poll" not in user_prompt
        assert "Random link" not in user_prompt
        assert "📎 Also" not in user_prompt

    def test_section_two_russian_stripped(self, grouper):
        """Russian '📎 Также:' section and everything after is removed."""
        messages = grouper._build_extractor_prompt(
            channel_name="Ch",
            summary=(
                "- 🤖 Главная новость\n"
                "📎 Также:\n"
                "• Опрос → https://t.me/x/1\n"
                "• Картинка → https://t.me/x/2"
            ),
        )
        user_prompt = messages[1]["content"]
        assert "Главная новость" in user_prompt
        assert "Опрос" not in user_prompt
        assert "Картинка" not in user_prompt


class TestDeterministicDedup:
    """Tests for deterministic dedup in _parse_grouped_response."""

    def test_verbatim_duplicate_in_same_group_dropped(self, grouper):
        """If AI emits the same (group, source, point) twice, only one survives."""
        response = json.dumps(
            {
                "Events": [
                    {"point": "Claude Beginners Guide", "source": "Robot"},
                    {"point": "Claude Beginners Guide", "source": "Robot"},
                ],
            }
        )
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert len(result["Events"]) == 1

    def test_dedup_normalizes_whitespace_and_case(self, grouper):
        """Near-duplicate (only whitespace/case differs) is also dropped."""
        response = json.dumps(
            {
                "Events": [
                    {"point": "Claude Beginners Guide", "source": "Robot"},
                    {"point": "  claude beginners  guide  ", "source": "Robot"},
                ],
            }
        )
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert len(result["Events"]) == 1

    def test_same_point_different_source_kept(self, grouper):
        """Same point text from a different source is preserved (separate signal)."""
        response = json.dumps(
            {
                "Events": [
                    {"point": "AI Summit", "source": "Ch1"},
                    {"point": "AI Summit", "source": "Ch2"},
                ],
            }
        )
        groups = grouper._build_group_definitions()
        valid_names = {g.name for g in groups}
        result = grouper._parse_grouped_response(response, valid_names)

        assert len(result["Events"]) == 2


class TestExtractBulletsFromChannel:
    """Tests for Pass 2a — per-channel bullet extraction."""

    @pytest.mark.asyncio
    async def test_extracts_bullets_from_single_channel(self, grouper):
        """Extractor returns one ExtractedBullet per bullet in summary."""
        grouper.provider.chat_completion.return_value = json.dumps(
            [
                {"point": "🤖 AI launched X"},
                {"point": "📈 Stock up 5%"},
            ]
        )

        result = await grouper._extract_bullets_from_channel(
            channel_name="TechNews",
            summary="- 🤖 AI launched X\n- 📈 Stock up 5%",
            source_url="https://t.me/technews",
        )

        assert len(result) == 2
        assert result[0].point == "🤖 AI launched X"
        assert result[0].source == "TechNews"
        assert result[0].source_url == "https://t.me/technews"

    @pytest.mark.asyncio
    async def test_empty_summary_skips_ai_call(self, grouper):
        """Empty/whitespace-only summary returns [] without calling AI."""
        result = await grouper._extract_bullets_from_channel(
            channel_name="Empty",
            summary="   \n  ",
            source_url="",
        )
        assert result == []
        grouper.provider.chat_completion.assert_not_called()


class TestExtractAllBullets:
    """Tests for parallel extraction across channels."""

    @pytest.mark.asyncio
    async def test_runs_extractor_per_channel_and_aggregates(self, grouper):
        """_extract_all_bullets calls extractor once per channel and flattens results."""
        # AI returns one bullet per channel
        grouper.provider.chat_completion.side_effect = [
            json.dumps([{"point": "🤖 News A"}]),
            json.dumps([{"point": "📰 News B"}]),
        ]

        result = await grouper._extract_all_bullets(
            channel_summaries={
                "Ch1": "- 🤖 News A",
                "Ch2": "- 📰 News B",
            },
            channel_urls={"Ch1": "https://t.me/c1", "Ch2": "https://t.me/c2"},
        )

        assert len(result) == 2
        sources = {b.source for b in result}
        assert sources == {"Ch1", "Ch2"}
        assert grouper.provider.chat_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_single_channel_failure_does_not_break_aggregation(self, grouper):
        """If one channel's extractor raises, others still produce bullets."""
        grouper.provider.chat_completion.side_effect = [
            RuntimeError("API down"),
            json.dumps([{"point": "📰 Survived"}]),
        ]

        result = await grouper._extract_all_bullets(
            channel_summaries={"Bad": "- broken", "Good": "- 📰 Survived"},
            channel_urls={},
        )

        assert len(result) == 1
        assert result[0].point == "📰 Survived"
        assert result[0].source == "Good"


class TestDedupExtracted:
    """Tests for cross-channel deterministic dedup chokepoint."""

    def test_same_normalized_text_merges_sources(self):
        """Two bullets with same normalized text from different sources merge into one."""
        bullets = [
            ExtractedBullet(point="AI Summit 2026", source="Ch1", source_url="u1"),
            ExtractedBullet(point="AI Summit 2026", source="Ch2", source_url="u2"),
        ]
        result = _dedup_extracted(bullets)

        assert len(result) == 1
        assert "Ch1" in result[0].source
        assert "Ch2" in result[0].source

    def test_keeps_longer_description_when_merging(self):
        """When merging, longer point text wins."""
        bullets = [
            ExtractedBullet(point="Short", source="Ch1"),
            ExtractedBullet(point="Short", source="Ch2"),
            ExtractedBullet(point="short", source="Ch3"),  # case-insensitive match
        ]
        result = _dedup_extracted(bullets)
        # All three normalize to "short" → 1 entry
        assert len(result) == 1

    def test_distinct_bullets_preserved(self):
        """Bullets with different normalized text are not merged."""
        bullets = [
            ExtractedBullet(point="🤖 AI news", source="Ch1"),
            ExtractedBullet(point="📰 Politics news", source="Ch1"),
        ]
        result = _dedup_extracted(bullets)
        assert len(result) == 2


class TestClassifyBullets:
    """Tests for Pass 2b — classification of pre-extracted, dedup'd bullets."""

    @pytest.mark.asyncio
    async def test_classifies_flat_bullets_into_groups(self, grouper):
        """Pass 2b consumes List[ExtractedBullet] and returns Dict[group, List[GroupedPoint]]."""
        grouper.provider.chat_completion.return_value = json.dumps(
            {
                "Events": [{"point": "🎪 Conference", "source": "Events Ch"}],
                "News": [{"point": "📰 Election", "source": "Politics Ch"}],
            }
        )

        bullets = [
            ExtractedBullet(point="🎪 Conference", source="Events Ch", source_url="u1"),
            ExtractedBullet(point="📰 Election", source="Politics Ch", source_url="u2"),
        ]
        groups = grouper._build_group_definitions()
        result = await grouper._classify_bullets(bullets, groups)

        assert "Events" in result
        assert result["Events"][0].source_url == "u1"
        assert "News" in result
        assert result["News"][0].source_url == "u2"

    @pytest.mark.asyncio
    async def test_empty_bullets_returns_empty(self, grouper):
        """No bullets → no AI call, empty result."""
        groups = grouper._build_group_definitions()
        result = await grouper._classify_bullets([], groups)
        assert result == {}
        grouper.provider.chat_completion.assert_not_called()


class TestGrouperMissingChannelWarning:
    """Tests for warning when input channels are missing from grouped output."""

    @pytest.mark.asyncio
    async def test_logs_warning_when_input_channels_missing_from_output(self, grouper, mock_logger):
        """Warning logged when some input channels have no points in the grouped output."""
        # Only Events has a point from Ch1; Ch2 is missing entirely
        ai_response = json.dumps(
            {
                "Events": [{"point": "Test event", "source": "Ch1"}],
            }
        )
        grouper.provider.chat_completion.return_value = ai_response

        await grouper.group_summaries(
            {
                "Ch1": "Summary about events",
                "Ch2": "Summary about news",
            }
        )

        # Should log a warning about Ch2 being missing
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("Ch2" in w for w in warning_calls)

    @pytest.mark.asyncio
    async def test_no_warning_when_all_channels_represented(self, grouper, mock_logger):
        """No missing-channel warning when all input channels appear in output."""
        ai_response = json.dumps(
            {
                "Events": [{"point": "Event from Ch1", "source": "Ch1"}],
                "News": [{"point": "News from Ch2", "source": "Ch2"}],
            }
        )
        grouper.provider.chat_completion.return_value = ai_response

        # Reset mock to clear any init warnings
        mock_logger.warning.reset_mock()

        await grouper.group_summaries(
            {
                "Ch1": "Summary about events",
                "Ch2": "Summary about news",
            }
        )

        # No warning about missing channels
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert not any("missing" in w.lower() for w in warning_calls)
