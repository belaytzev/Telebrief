# Digest Mode - Topic-Grouped Output

## Overview
Add a new "digest" output mode that re-sorts per-channel AI summaries into configurable topic groups (e.g., Events, News, Sport, Other). The existing per-channel mode remains the default. In digest mode, a second AI pass classifies bullet points from all channel summaries into user-defined topic groups, then sends each group as a separate Telegram message.

Key benefits:
- Cross-channel topic view instead of per-channel view
- User-configurable groups with AI-powered classification
- Source attribution via channel name on every bullet point (no deep links — AI summaries don't preserve structured URLs reliably)

## Context (from discovery)
- Files/components involved: `src/config_loader.py`, `src/core.py`, `src/formatter.py`, `src/ui_strings.py`, `src/ai_providers.py`, `config.yaml.example`
- New file: `src/grouper.py`
- Related patterns: `DigestFormatter` uses `self._ui = get_ui_strings()` pattern; `Summarizer` calls `AIProvider.chat_completion()`; `core.py` has `generate_and_send_channel_digests()` as the per-channel orchestration function
- Dependencies: reuses existing `AIProvider` for the grouping AI call; reuses `DigestSender.send_channel_messages_with_tracking()` for sending

## Development Approach
- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- Make small, focused changes
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task
- **CRITICAL: all tests must pass before starting next task** - no exceptions
- **CRITICAL: update this plan file when scope changes during implementation**
- Run tests after each change
- Maintain backward compatibility — existing `digest_mode: "channel"` (or unset) must behave identically to current code

## Testing Strategy
- **Unit tests**: required for every task
- Test commands: `uv run pytest tests/ -v`, `uv run mypy src/`, `uv tool run ruff check src/ tests/`

## Progress Tracking
- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with + prefix
- Document issues/blockers with ! prefix
- Update plan if implementation deviates from original scope

## Implementation Steps

### Task 1: Add config settings for digest mode

**Files:**
- Modify: `src/config_loader.py`
- Modify: `config.yaml.example`
- Modify: `tests/test_config_loader.py`

- [x] Add `DigestGroupConfig` dataclass to `config_loader.py` with fields: `name: str`, `description: str`
- [x] Add `digest_mode: str = "channel"` field to `Settings` dataclass (valid values: "channel", "digest")
- [x] Add `digest_groups: List[DigestGroupConfig]` field to `Settings` dataclass (default: empty list)
- [x] Parse `digest_groups` from YAML in `load_config()` — map each entry to `DigestGroupConfig`
- [x] Update `Settings(...)` constructor call in `load_config()` to pass `digest_mode` and `digest_groups`
- [x] Add validation: if `digest_mode` not in ("channel", "digest"), raise ValueError
- [x] Add validation: if `digest_mode == "digest"` and `digest_groups` is empty, log a warning ("digest mode enabled but no digest_groups configured — all content will go to 'Other'")
- [x] Add `digest_mode` and `digest_groups` example to `config.yaml.example` with comments
- [x] Write tests: valid digest config loads correctly
- [x] Write tests: missing digest_groups defaults to empty list, digest_mode defaults to "channel"
- [x] Write tests: invalid digest_mode value raises ValueError
- [x] Write tests: digest_mode "digest" with empty digest_groups logs warning
- [x] Run tests — must pass before Task 2

### Task 2: Add UI strings for digest groups

**Files:**
- Modify: `src/ui_strings.py`
- Modify: `tests/test_ui_strings.py`

- [x] Add new keys to all language dicts in `_STRINGS`: `"group_other"` (name for implicit Other group), `"group_items_count"` ("{count} items"), `"groups_processed"` ("Groups"), `"from_channel"` ("from {channel}")
- [x] Write tests: new keys present in all languages (English, Russian, Spanish, German, French)
- [x] Run tests — must pass before Task 3

### Task 3: Create DigestGrouper module

**Files:**
- Create: `src/grouper.py`
- Create: `tests/test_grouper.py`

- [ ] Create `GroupedPoint` dataclass: `point: str`, `source: str` (channel name only — no deep links, since AI summaries don't preserve structured URLs reliably)
- [ ] Create `DigestGrouper` class with `__init__(self, config: Config, logger: logging.Logger)` — instantiate AI provider via `create_provider()` using same pattern as `Summarizer.__init__`
- [ ] Implement `_build_group_definitions()` — returns list of groups including implicit "Other" if not user-defined
- [ ] Implement `_build_classification_prompt()` — system prompt instructing AI to classify bullet points into groups, output JSON format: `{"GroupName": [{"point": "...", "source": "ChannelName"}]}`
- [ ] Implement `_parse_grouped_response()` — strip markdown code fences (` ```json...``` `) before parsing, then parse AI JSON response into `Dict[str, List[GroupedPoint]]`, fallback: put everything in "Other" on parse failure
- [ ] Implement `async group_summaries(channel_summaries: Dict[str, str]) -> Dict[str, List[GroupedPoint]]` — main method: builds prompt from all channel summaries, calls AI via provider, parses response
- [ ] Write tests: `_build_group_definitions()` adds implicit "Other" when not in config
- [ ] Write tests: `_build_group_definitions()` does NOT duplicate "Other" when already in config
- [ ] Write tests: `_parse_grouped_response()` with valid JSON returns correct dict
- [ ] Write tests: `_parse_grouped_response()` with JSON wrapped in markdown code fences parses correctly
- [ ] Write tests: `_parse_grouped_response()` with invalid JSON falls back to "Other"
- [ ] Write tests: `group_summaries()` end-to-end with mocked AI provider
- [ ] Run tests — must pass before Task 4

### Task 4: Add formatter methods for group messages

**Files:**
- Modify: `src/formatter.py`
- Modify: `tests/test_formatter.py`

- [ ] Add `_pick_group_emoji(group_name: str) -> str` method — mapping: Events/event -> "🎪", News/news -> "📰", Sport/sport -> "⚽", Other/other -> "📌", default -> "📌"
- [ ] Add `format_group_message(group_name: str, points: List[GroupedPoint], hours: int) -> str` method — formats a single group as a Telegram message with header, bullets with source attribution, and stats footer
- [ ] Add `format_group_summary_message(group_names: List[str], total_points: int, hours: int) -> str` method — header message listing active groups and total points
- [ ] Enforce 4096 char Telegram limit in `format_group_message()` with truncation (same pattern as `format_channel_message()`)
- [ ] Write tests: `_pick_group_emoji()` returns correct emoji for known groups
- [ ] Write tests: `format_group_message()` produces expected output format with source attribution
- [ ] Write tests: `format_group_message()` truncates at 4096 chars
- [ ] Write tests: `format_group_summary_message()` produces expected header format
- [ ] Write tests: `format_group_message()` with empty points list (should not happen but be defensive)
- [ ] Run tests — must pass before Task 5

### Task 5: Add digest mode orchestration to core.py

**Files:**
- Modify: `src/core.py`
- Modify: `tests/test_core.py`

- [ ] Add `generate_and_send_digest_grouped()` as a standalone async function that duplicates the collect+summarize steps from the per-channel flow (acceptable duplication for two callers — no shared helper extraction needed). Flow: collect -> summarize -> group -> format per-group -> cleanup -> send
- [ ] Skip empty groups (no message sent)
- [ ] Use `formatter.format_group_summary_message()` for header and `formatter.format_group_message()` for each group
- [ ] Reuse `sender.send_channel_messages_with_tracking()` — pass list of `(group_name, formatted_message)` tuples
- [ ] Add mode switch at the top of `generate_and_send_channel_digests()`: if `config.settings.digest_mode == "digest"`, delegate to `generate_and_send_digest_grouped()` and return early
- [ ] Write tests: `generate_and_send_digest_grouped()` calls grouper and formatter correctly (mock AI + sender)
- [ ] Write tests: mode switch in `generate_and_send_channel_digests()` delegates to grouped function when mode is "digest"
- [ ] Write tests: mode switch uses existing per-channel flow when mode is "channel" (backward compat)
- [ ] Run tests — must pass before Task 6

### Task 6: Verify acceptance criteria

- [ ] Verify existing per-channel mode works identically (no regression)
- [ ] Verify digest mode config is optional — missing `digest_mode` defaults to "channel"
- [ ] Verify implicit "Other" group catches unmatched points
- [ ] Verify empty groups produce no message
- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Run type check: `uv run mypy src/`
- [ ] Run linter: `uv tool run ruff check src/ tests/`

### Task 7: [Final] Update documentation

- [ ] Update `config.yaml.example` comments if needed after implementation
- [ ] Move this plan to `docs/plans/completed/`

## Technical Details

### Config structure
```yaml
settings:
  digest_mode: "digest"  # "channel" (default) | "digest"
  digest_groups:
    - name: "Events"
      description: "Conferences, meetups, releases, launches, announcements"
    - name: "News"
      description: "Politics, economy, world affairs, breaking news"
    - name: "Sport"
      description: "Sports results, transfers, tournaments, matches"
  # "Other" group is implicit — always added as catch-all
```

### Data structures
```python
@dataclass
class DigestGroupConfig:
    name: str
    description: str

@dataclass
class GroupedPoint:
    point: str
    source: str   # channel name (no deep links — AI summaries don't preserve structured URLs)
```

### AI classification prompt (grouper)
- Input: concatenated channel summaries with channel names as section headers
- Instructions: extract individual bullet points, classify each into defined groups
- Output format: JSON dict mapping group names to lists of `{"point": "...", "source": "ChannelName"}`
- Response parsing: strip markdown code fences (` ```json...``` `) before JSON.loads()
- Fallback: if JSON parse fails after stripping, all content goes to "Other" (no content loss)
- Language: respects `output_language` setting — instructs AI to preserve original language of points
- Provider: instantiated via `create_provider()` using same pattern as `Summarizer.__init__`

### Processing flow (digest mode)
```
1. COLLECT messages per channel (unchanged)
2. SUMMARIZE per channel via AI (unchanged)
3. GROUP: DigestGrouper.group_summaries(channel_summaries)
   -> Dict[group_name, List[GroupedPoint]]
4. FORMAT: per-group Telegram messages + summary header
5. CLEANUP old digests (existing)
6. SEND: summary header + per-group messages via existing sender
```

### Group emoji mapping
| Group name (case-insensitive) | Emoji |
|-------------------------------|-------|
| events, event | 🎪 |
| news | 📰 |
| sport, sports | ⚽ |
| other | 📌 |
| (default) | 📌 |

## Post-Completion

**Manual verification:**
- Test with real Telegram channels to verify AI classification quality
- Verify per-group messages render correctly in Telegram (Markdown parsing)
- Test with various group configurations (1 group, many groups, no groups)
- Test with channels producing no content for some groups (empty group skipping)
