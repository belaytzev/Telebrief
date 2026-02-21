# Fix TOC Order and UI Language Support

## Overview

Two bugs to fix:

1. **TOC order**: The Table of Contents summary message is sent last (after all channel messages),
   but it should appear first as a navigation header. Also, `tg://openmessage` links work on
   mobile Telegram but not on Telegram Desktop — this is a platform limitation of the current
   approach.

2. **UI language**: All structural/stats messages in `formatter.py` and `bot_commands.py` are
   hardcoded in Russian, ignoring the `output_language` config setting. The AI-generated summaries
   already respect `output_language` (via `summarizer.py`), but the surrounding UI chrome does not.

## Context (from discovery)

- Files involved: `src/sender.py`, `src/formatter.py`, `src/bot_commands.py`
- New file needed: `src/ui_strings.py` (shared translation strings for formatter + bot_commands)
- Tests: `tests/test_sender.py`, `tests/test_formatter.py`, `tests/test_bot_commands.py`
- `output_language` default: `"Russian"` (from `config_loader.py:43`)
- `self.bot_id` extracted from token: `int(config.telegram_bot_token.split(":")[0])` (sender.py:38)

## Development Approach

- **Testing approach**: TDD — write failing tests first, then implement
- Complete each task fully before moving to the next
- All tests must pass before starting next task
- Run `uv run pytest tests/ -x` after each task

## Technical Details

### Bug 1 fix — TOC order (sender.py)

Current flow (wrong):
1. `_send_channel_messages_loop()` → sends all channel messages → collects message IDs
2. `_send_summary_message()` → sends summary + TOC keyboard last

New flow:
1. Send placeholder summary (no keyboard) → get `summary_id`
2. `_send_channel_messages_loop()` → sends channel messages → collects message IDs
3. `bot.edit_message_reply_markup(summary_id, keyboard)` → add TOC to existing summary

This requires a new `_edit_summary_keyboard()` helper and restructuring of
`send_channel_messages_with_tracking()`.

### Bug 2 fix — UI strings (ui_strings.py)

New module `src/ui_strings.py` with a `get_ui_strings(language: str) -> dict` function.
Keys map to translated strings. Supported languages with fallback to English:

```python
# Keys needed:
"daily_digest"         # "Daily Digest" / "Ежедневный дайджест"
"overview"             # "Brief Overview" / "Краткий обзор"
"stats_header"         # "Statistics" / "Статистика"
"channels"             # "channels" / "каналов"
"messages_processed"   # "messages processed" / "сообщений обработано"
"digest_for"           # "Digest for" / "Дайджест за"
"period_last_hours"    # "Period: last {hours} hours" / "Период: последние {hours} часов"
"messages_count"       # "Messages processed" / "Обработано сообщений"
"last_hours"           # "Last {hours} hours" / "За последние {hours} часов"
"truncated"            # "...(truncated due to length limit)" / "...(усечено из-за лимита длины)"
"digest_completed"     # "Digest completed" / "Дайджест завершён"
"channels_processed"   # "Channels processed" / "Обработано каналов"
"total_messages"       # "Total messages" / "Всего сообщений"
"period"               # "Period" / "Период"
# bot_commands keys:
"cmd_start_desc"       # "Start the bot" / "Начать работу с ботом"
"cmd_digest_desc"      # "Generate digest for 24 hours"
"cmd_cleanup_desc"     # "Delete old digests"
"cmd_status_desc"      # "Show status and settings"
"cmd_help_desc"        # "Show help"
"generating_digest"    # "⏳ Generating digest..."
"digest_done"          # "✅ Digest ready!..."
"digest_error"         # "❌ Error generating digest."
"digest_exception"     # "❌ An error occurred..."
"cleaning_up"          # "🧹 Deleting previous digests..."
"cleanup_done"         # "✅ Previous digests deleted!"
"cleanup_partial"      # "⚠️ Failed to delete some messages..."
"cleanup_error"        # "❌ Error during cleanup."
"status_header"        # "📊 **Telebrief Status**"
"provider_label"       # "🤖 Provider"
"model_label"          # "🧠 Model"
"channels_configured"  # "📺 Channels configured"
"auto_cleanup_label"   # "🧹 Auto-cleanup"
"enabled"              # "Enabled" / "Включена"
"disabled"             # "Disabled" / "Выключена"
"next_digest"          # "⏰ Next digest"
"scheduler_not_running"# "⏰ Scheduler not running"
"available_commands"   # "**Available commands:**"
"help_title"           # "🤖 **Telebrief - Telegram Digest Generator**"
"help_intro"           # intro sentence about AI digests
"help_commands_header" # "**Commands:**"
"help_auto_mode"       # "**Automatic mode:**"
"help_auto_desc"       # daily schedule description
"help_features"        # "**Features:**"
```

Languages to implement initially: `English` (default/fallback), `Russian`, `Spanish`, `German`, `French`.

## Progress Tracking

- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix

## Implementation Steps

### Task 1: Fix TOC order in sender.py (TDD)

- [x] write failing test: `test_summary_sent_before_channel_messages` — verify summary message
      sent before channel messages in `send_channel_messages_with_tracking`
- [x] write failing test: `test_summary_keyboard_edited_after_channels` — verify
      `edit_message_reply_markup` called with summary_id and TOC keyboard after channels sent
- [x] run tests — confirm they fail (expected)
- [x] add `_edit_summary_keyboard(user_id, summary_id, keyboard)` method to `DigestSender`
      using `bot.edit_message_reply_markup(chat_id=user_id, message_id=summary_id, reply_markup=keyboard)`
- [x] refactor `send_channel_messages_with_tracking()`: send summary first (no keyboard),
      then `_send_channel_messages_loop()`, then call `_edit_summary_keyboard()`
- [x] handle case where all channels fail (no channel_id_map): edit message to remove keyboard
      placeholder gracefully (or skip edit)
- [x] run tests — must pass before task 2

### Task 2: Create src/ui_strings.py (TDD)

- [x] write failing tests in `tests/test_ui_strings.py`:
      - `test_get_ui_strings_english` — verify English returns correct keys
      - `test_get_ui_strings_russian` — verify Russian returns Russian strings
      - `test_get_ui_strings_unknown_language_falls_back_to_english`
      - `test_all_required_keys_present_for_each_language`
- [x] run tests — confirm they fail (expected)
- [x] create `src/ui_strings.py` with `get_ui_strings(language: str) -> dict` supporting
      English (default), Russian, Spanish, German, French
- [x] run tests — must pass before task 3

### Task 3: Update formatter.py to use ui_strings (TDD)

- [x] write failing tests in `tests/test_formatter.py`:
      - `test_create_header_uses_output_language` — English config → English header
      - `test_format_summary_message_uses_output_language`
      - `test_create_statistics_uses_output_language`
      - `test_format_channel_message_stats_uses_output_language`
      - `test_overview_section_label_uses_output_language`
      - `test_truncation_message_uses_output_language`
- [x] run tests — confirm they fail (expected)
- [x] update `DigestFormatter.__init__` to read `output_language` from config and call
      `get_ui_strings(output_language)` storing result as `self._ui`
- [x] update `_create_header()`: use `self._ui["daily_digest"]`, remove Russian month translation
      (use `strftime("%d %B %Y")` which produces English month names, let the AI content handle language)
- [x] update `create_digest()` line 67: use `self._ui["overview"]`
- [x] update `format_channel_message()`: use `self._ui` keys for stats labels and truncation message
- [x] update `format_summary_message()`: replace all Russian strings with `self._ui` keys
- [x] update `_create_statistics()`: replace all Russian strings with `self._ui` keys
- [x] run tests — must pass before task 4

### Task 4: Update bot_commands.py to use ui_strings (TDD)

- [x] write failing tests in `tests/test_bot_commands.py`:
      - `test_setup_bot_menu_uses_output_language` — with English config, commands have English descriptions
      - `test_handle_digest_processing_message_uses_output_language`
      - `test_handle_digest_success_message_uses_output_language`
      - `test_handle_digest_error_message_uses_output_language`
      - `test_handle_cleanup_messages_use_output_language`
      - `test_handle_status_uses_output_language`
      - `test_handle_help_uses_output_language`
- [x] run tests — confirm they fail (expected)
- [x] update `BotCommandHandler.__init__` to call `get_ui_strings(config.settings.output_language)`
      storing as `self._ui`
- [x] update `setup_bot_menu()`: use `self._ui` keys for all `BotCommand` descriptions
- [x] update `handle_digest()`: use `self._ui` for processing/success/error messages
- [x] update `handle_cleanup()`: use `self._ui` for all reply texts
- [x] update `handle_status()`: use `self._ui` for all status labels and values
- [x] update `handle_help()`: use `self._ui` for all help text (keep `{schedule}`, `{output_lang}`,
      `{provider}` dynamic interpolations)
- [x] run tests — must pass before task 5

### Task 5: Verify acceptance criteria

- [x] verify TOC summary appears first in chat flow (review send order in tests)
- [x] verify `edit_message_reply_markup` called with correct message ID
- [x] verify all formatter strings use `output_language` (no hardcoded "Статистика" etc.)
- [x] verify all bot_commands strings use `output_language`
- [x] run full test suite: `uv run pytest tests/ -v` — 162 passed
- [x] run linter: `uv tool run ruff check src/ tests/` — all checks passed
- [x] run type checker: `uv run mypy src/` — no issues found in 12 source files
- [x] verify test coverage: 68.38% (above 49% threshold)

### Task 6: Update documentation

- [x] update README.md if any new behaviour needs documenting
- [x] update project knowledge docs if new patterns discovered

*Note: ralphex automatically moves completed plans to `docs/plans/completed/`*

## Post-Completion

**Manual verification:**
- Test with Telegram mobile client: verify TOC appears at top, links navigate to channel sections
- Test with Telegram Desktop: verify TOC appears at top (links are known not to work on Desktop — platform limitation of `tg://openmessage`)
- Switch `output_language` to `"English"` in config, generate digest: verify all labels in English
- Switch `output_language` to `"Spanish"`, verify all labels in Spanish

**Note on TOC links on Desktop:**
`tg://openmessage?user_id={bot_id}&message_id={msg_id}` is an undocumented Telegram deep link that works on iOS/Android but not on Telegram Desktop. This is a known platform limitation with no publicly available workaround for private bot chats. The `https://t.me/c/` format is only available for channels/supergroups.
