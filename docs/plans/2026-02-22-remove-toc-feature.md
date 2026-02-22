# Remove TOC Feature

## Overview

Remove the Table of Contents (TOC) inline keyboard navigation feature entirely from the codebase. The feature sends a summary message first with an inline keyboard that links to each channel digest. Removing it means the summary message is still sent (as a plain digest header with no keyboard), but all TOC keyboard building, TOC callback handling, and related tests are deleted. The website feature card and README mention of TOC are also removed.

## Context

- Files involved:
  - `src/formatter.py` — `build_toc_keyboard()` method + `InlineKeyboardButton/Markup` imports
  - `src/sender.py` — `_edit_summary_keyboard()`, `channel_id_map` tracking in `_send_channel_messages_loop`, TOC keyboard logic in `send_channel_messages_with_tracking`, `InlineKeyboardMarkup` import
  - `src/bot_commands.py` — `handle_toc_callback()` method + `CallbackQueryHandler` import/registration
  - `src/ui_strings.py` — `"toc_sent_below"` key in all 5 language dicts
  - `tests/test_formatter.py` — 5 TOC keyboard tests
  - `tests/test_sender.py` — ~8 TOC-related tests
  - `tests/test_bot_commands.py` — 3 TOC callback tests
  - `website/src/pages/index.astro` — "Table of Contents Navigation" feature card
  - `README.md` — 2 TOC mentions
- Related patterns: `format_summary_message()` in formatter stays (it's the header message, just without TOC keyboard). `send_channel_messages_with_tracking()` stays but drops TOC keyboard logic.

## Development Approach

- **Testing approach**: Regular (modify code, update tests to match)
- Remove the feature completely — no config flag, no backwards shim
- All tests must pass after each task before moving to the next
- The summary message flow (send placeholder first, send channels, save IDs) is preserved — only the TOC keyboard attachment is removed

## Implementation Steps

### Task 1: Remove TOC from formatter

**Files:**
- Modify: `src/formatter.py`

- [x] Delete `build_toc_keyboard()` method entirely (lines 264–314)
- [x] Remove `InlineKeyboardButton` and `InlineKeyboardMarkup` from the import (line 9)
- [x] Update `format_summary_message()` docstring to remove "TOC placeholder" wording
- [x] Run `uv run pytest tests/test_formatter.py -v` — expect TOC tests to fail (they will be removed in task 3)

### Task 2: Remove TOC from sender

**Files:**
- Modify: `src/sender.py`

- [x] Remove `InlineKeyboardMarkup` from import (line 9)
- [x] Delete `_edit_summary_keyboard()` method (lines 401–423)
- [x] In `_send_channel_messages_loop()`: remove `channel_id_map` list and `channel_id_map.append(...)` line; return only `(sent_message_ids, success_count, failed_channels)`
- [x] In `send_channel_messages_with_tracking()`: remove `channel_id_map` from the unpacking of `_send_channel_messages_loop`; remove the `if summary_message and summary_id is not None and success_count > 0:` TOC keyboard block; keep the orphaned-summary cleanup branch (the `elif summary_id is not None and success_count == 0:` block stays)
- [x] Run `uv run pytest tests/test_sender.py -v` — expect TOC-related tests to fail (they will be removed in task 3)

### Task 3: Remove TOC from bot_commands

**Files:**
- Modify: `src/bot_commands.py`

- [x] Remove `CallbackQueryHandler` from the import (line 11)
- [x] Remove `self.app.add_handler(CallbackQueryHandler(self.handle_toc_callback, pattern=r"^toc:"))` from `setup_application()` (line 56)
- [x] Delete `handle_toc_callback()` method entirely (lines 264–325)
- [x] Run `uv run pytest tests/test_bot_commands.py -v` — expect TOC callback tests to fail

### Task 4: Remove toc_sent_below from ui_strings

**Files:**
- Modify: `src/ui_strings.py`

- [x] Remove the `"toc_sent_below"` key-value pair from all 5 language dicts (English, Russian, Spanish, German, French)
- [x] Run `uv run pytest tests/ -v` — may see remaining import-level failures until test cleanup

### Task 5: Remove TOC tests

**Files:**
- Modify: `tests/test_formatter.py`
- Modify: `tests/test_sender.py`
- Modify: `tests/test_bot_commands.py`

- [x] In `tests/test_formatter.py`: delete all 5 `build_toc_keyboard` tests (lines 137–220 approx) and the `from telegram import InlineKeyboardMarkup` import if it becomes unused
- [x] In `tests/test_sender.py`: delete tests that reference TOC keyboard, channel_id_map, or toc callback:
  - `test_send_channel_messages_with_tracking` (asserts `edit_message_reply_markup` called)
  - `test_send_channel_messages_loop_channel_id_map`
  - `test_send_channel_messages_loop_channel_id_map_with_failure`
  - `test_summary_message_sent_with_toc_keyboard`
  - `test_toc_keyboard_uses_callback_data_for_private_chat`
  - `test_toc_keyboard_not_edited_when_all_channels_fail`
  - `test_summary_toc_keyboard_contains_only_successful_channels`
  - `test_summary_keyboard_edited_with_toc_after_channels`
  - Update `test_send_channel_messages_with_tracking` to not assert `edit_message_reply_markup` if the test is kept for tracking-only behavior
- [x] In `tests/test_bot_commands.py`: delete 3 TOC callback tests:
  - `test_handle_toc_callback_basic_group`
  - `test_handle_toc_callback_malformed_data`
  - `test_handle_toc_callback_telegram_error`
  - Remove `_make_callback_update` helper (only used by TOC tests) if unused
- [x] Remove `from telegram import InlineKeyboardMarkup` import in `tests/test_sender.py` if unused
- [x] Run `uv run pytest tests/ -v` — must be fully green

### Task 6: Remove TOC from website

**Files:**
- Modify: `website/src/pages/index.astro`

- [x] Remove the "Table of Contents Navigation" feature card div (lines 117–122 approx):
  ```html
  <div class="card feature-card">
    <div class="icon">🗂️</div>
    <h3>Table of Contents Navigation</h3>
    <p>Each digest includes an interactive summary with inline navigation buttons, letting you jump directly to any channel's summary with a single tap.</p>
  </div>
  ```
- [x] No test needed for website change

### Task 7: Remove TOC from README

**Files:**
- Modify: `README.md`

- [ ] Remove the `- 🗂️ **Table of Contents Navigation** - ...` bullet point from the features list
- [ ] Remove the inline-keyboard mention in the digest description paragraph (line 114: "with inline keyboard buttons")
- [ ] No test needed for README change

### Task 8: Update MEMORY.md

**Files:**
- Modify: `/Users/belaytzev/.claude-personal/projects/-Users-belaytzev-Documents-Sync-Personal-Telebrief/memory/MEMORY.md`

- [ ] Remove the TOC-related entries from the "Key Patterns" section in MEMORY.md (the 4 bullet points about TOC summary, keyboard buttons, private/supergroup/basic group behavior, and `handle_toc_callback` auth behavior)

### Task 9: Verify acceptance criteria

- [ ] Run full test suite: `uv run pytest tests/ -v` — must pass
- [ ] Run type check: `uv run mypy src/`
- [ ] Run linter: `uv tool run ruff check src/ tests/`
- [ ] Confirm no `toc` or `TOC` references remain in `src/` or `tests/`: `grep -r "toc\|TOC\|build_toc\|handle_toc\|toc_sent" src/ tests/`
- [ ] Move this plan to `docs/plans/completed/`
