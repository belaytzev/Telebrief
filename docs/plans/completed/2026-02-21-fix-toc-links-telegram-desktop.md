# Fix TOC Links Not Working on Telegram Desktop

## Overview

TOC (Table of Contents) inline keyboard buttons in the digest summary message use
`tg://openmessage?user_id=...&message_id=...` URLs for private chats. This URL scheme
is only handled by Telegram Mobile apps; on Telegram Desktop the buttons are dead
(clicking does nothing). The fix replaces URL buttons with callback_data buttons for
private chats, and adds a callback handler that copies the original channel message
back to the chat — working on all platforms.

## Context

- Files involved:
  - `src/formatter.py` — `build_toc_keyboard` generates the InlineKeyboardMarkup
  - `src/sender.py` — `send_channel_messages_with_tracking` calls `build_toc_keyboard`
  - `src/bot_commands.py` — sets up application handlers; must register the new callback handler
  - `tests/test_formatter.py` — tests for `build_toc_keyboard`; one test must be updated
  - `tests/test_bot_commands.py` — needs new test for the callback handler (create if absent)

- Root cause (sender.py:468):
  ```python
  toc_peer_id = self.bot_id if user_id > 0 else user_id
  keyboard = self.formatter.build_toc_keyboard(channel_id_map, toc_peer_id)
  ```
  For private chats, `toc_peer_id = bot_id` (positive), so `build_toc_keyboard`
  generates `tg://openmessage` URLs that do not work on Telegram Desktop.

- Existing behavior kept: for group/channel chats (chat_id < 0) `https://t.me/c/...`
  URLs are already correct and remain unchanged.

## Development Approach

- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- CRITICAL: every task MUST include new/updated tests
- CRITICAL: all tests must pass before starting next task
- Run `uv run pytest tests/ -v` after each task
- Type check: `uv run mypy src/`
- Lint: `uv tool run ruff check src/ tests/`

## Implementation Steps

### Task 1: Update `build_toc_keyboard` to use callback buttons for private chats

**Files:**
- Modify: `src/formatter.py`

- [x] In `build_toc_keyboard`, change the `if chat_id > 0` branch:
  - Instead of `url = f"tg://openmessage?..."`, generate
    `callback_data = f"toc:{chat_id}:{message_id}"` (max 64 bytes, safe for all realistic IDs)
  - Use `InlineKeyboardButton(text=label, callback_data=...)` for this branch
  - Leave the `else` (negative chat_id) branch unchanged — still uses `url=f"https://t.me/c/..."`
- [x] Update the docstring to reflect the dual-mode behaviour

### Task 2: Update `sender.py` to pass `user_id` instead of `bot_id`

**Files:**
- Modify: `src/sender.py`

- [x] In `send_channel_messages_with_tracking`, change:
  ```python
  toc_peer_id = self.bot_id if user_id > 0 else user_id
  ```
  to:
  ```python
  toc_peer_id = user_id
  ```
  The formatter now handles private vs group distinction internally using the sign of `chat_id`.

### Task 3: Add callback handler in `bot_commands.py`

**Files:**
- Modify: `src/bot_commands.py`

- [x] Import `CallbackQueryHandler` from `telegram.ext`
- [x] Register handler in `setup_application`:
  ```python
  self.app.add_handler(CallbackQueryHandler(self.handle_toc_callback, pattern=r"^toc:"))
  ```
- [x] Implement `handle_toc_callback`:
  - Parse `callback_data`: split on `:` to get `user_id` (int) and `message_id` (int)
  - Verify the calling user is authorized (`self.is_authorized(update.effective_user.id)`)
  - Call `await context.bot.copy_message(chat_id=user_id, from_chat_id=user_id, message_id=message_id)`
  - Answer the callback query with `await update.callback_query.answer()` (clears the spinner)
  - Log success or error; on `TelegramError`, answer the callback with an error message string

### Task 4: Update tests for `build_toc_keyboard` and add callback handler tests

**Files:**
- Modify: `tests/test_formatter.py`
- Create or modify: `tests/test_bot_commands.py`

- [x] In `test_formatter.py`, update `test_build_toc_keyboard_private_chat`:
  - Remove assertion on `btn.url`
  - Assert `btn.callback_data == "toc:123456:101"` and `btn1.callback_data == "toc:123456:202"`
  - Assert `btn.url is None`
- [x] Keep `test_build_toc_keyboard_supergroup_chat` unchanged (URL path)
- [x] Add `test_build_toc_keyboard_one_button_per_row` still passes (labels unaffected)
- [x] In `test_bot_commands.py`, add `test_handle_toc_callback_success`:
  - Mock `update.callback_query.data = "toc:123456789:42"`
  - Mock `update.effective_user.id = 123456789` (authorized)
  - Mock `context.bot.copy_message = AsyncMock()`
  - Mock `update.callback_query.answer = AsyncMock()`
  - Call `await handler.handle_toc_callback(update, context)`
  - Assert `copy_message` called with `chat_id=123456789, from_chat_id=123456789, message_id=42`
  - Assert `answer` called once
- [x] Add `test_handle_toc_callback_unauthorized`:
  - Same but `update.effective_user.id = 999999` (not the target user)
  - Assert `copy_message` NOT called

### Task 5: Verify acceptance criteria

- [x] Run full test suite: `uv run pytest tests/ -v` — must pass
- [x] Run type check: `uv run mypy src/` — must pass
- [x] Run linter: `uv tool run ruff check src/ tests/` — must pass
- [x] Verify test coverage: `uv run pytest tests/ --cov=src --cov-report=term-missing`

### Task 6: Update documentation

- [x] Update MEMORY.md: replace `tg://openmessage` note with the new callback button approach
- [x] Move this plan to `docs/plans/completed/`
