# Fix TOC: Use Deep Links Instead of copy_message

## Overview

TOC (Table of Contents) buttons in private chats currently call `copy_message()` which resends a
duplicate copy of the channel summary into the chat. Replace this with `tg://openmessage` URL
buttons that navigate to the original message without creating copies.

## Context

- Files involved:
  - `src/formatter.py` — `build_toc_keyboard()` builds the inline keyboard
  - `src/bot_commands.py` — `handle_toc_callback()` handles button clicks
  - `tests/test_formatter.py` — tests for `build_toc_keyboard`
  - `tests/test_bot_commands.py` — tests for `handle_toc_callback`
- Root cause: private chat buttons use `callback_data="toc:{chat_id}:{message_id}"`, and the
  callback handler calls `bot.copy_message()` which makes a new copy instead of navigating
- Fix: change private chat (chat_id > 0) buttons to URL buttons using
  `tg://openmessage?user_id={chat_id}&message_id={message_id}`, which navigates to the original
  message on Telegram mobile and recent Telegram Desktop
- Supergroup/channel buttons (`chat_id < 0, starts with -100`) already use `https://t.me/c/`
  URLs — leave those unchanged
- Basic group buttons (`chat_id < 0, does NOT start with -100`) keep using callback + copy_message
  since there is no universal deep link for basic group messages

## Development Approach

- **Testing approach**: Regular (update implementation, then update tests)
- Complete each task fully before moving to the next
- All tests must pass before marking a task done

## Implementation Steps

### Task 1: Update `build_toc_keyboard` in `formatter.py`

**Files:**
- Modify: `src/formatter.py`

- [x] In `build_toc_keyboard`, change the `chat_id > 0` branch to build a URL button using
  `tg://openmessage?user_id={chat_id}&message_id={message_id}` instead of `callback_data`
- [x] Remove the now-unused `toc:{chat_id}:{message_id}` callback_data path for private chats
- [x] Keep the basic group (`chat_id < 0, not -100`) branch using callback_data unchanged
- [x] Keep the supergroup/channel (`chat_id < 0, starts with -100`) branch using `https://t.me/c/`
  URLs unchanged
- [x] Update the docstring to reflect the new behavior

### Task 2: Simplify `handle_toc_callback` in `bot_commands.py`

**Files:**
- Modify: `src/bot_commands.py`

- [x] `handle_toc_callback` is now only reachable for basic group callbacks (private chats no
  longer emit callback_data buttons)
- [x] Remove the `target_chat_id > 0` private-chat security check (private chats never hit this
  handler anymore)
- [x] Keep the basic group handling (negative chat_id) logic that calls `copy_message`
- [x] Update the docstring to reflect the reduced scope of this handler

### Task 3: Update tests for `build_toc_keyboard`

**Files:**
- Modify: `tests/test_formatter.py`

- [ ] Update `test_build_toc_keyboard_private_chat` to assert that buttons have a `url` property
  (not `callback_data`) and that the URL matches
  `tg://openmessage?user_id=123456&message_id=101` / `...message_id=202`
- [ ] Verify `test_build_toc_keyboard_supergroup_chat` still passes (no change needed)
- [ ] Verify `test_build_toc_keyboard_negative_non_supergroup_chat` still passes (callback_data
  for basic groups, no change needed)
- [ ] Run `uv run pytest tests/test_formatter.py -v` — must pass before task 4

### Task 4: Update tests for `handle_toc_callback`

**Files:**
- Modify: `tests/test_bot_commands.py`

- [ ] Remove or repurpose `test_handle_toc_callback_success` — private chats no longer hit this
  handler; replace with a test that verifies the basic-group callback still works
- [ ] Remove `test_handle_toc_callback_unauthorized` — private chat security no longer applied
  here (URL buttons don't go through the callback at all)
- [ ] Remove `test_handle_toc_callback_user_id_mismatch` — same reason as above
- [ ] Keep `test_handle_toc_callback_basic_group` and verify it still passes
- [ ] Keep `test_handle_toc_callback_malformed_data` — still relevant for basic groups
- [ ] Keep `test_handle_toc_callback_telegram_error` — still relevant
- [ ] Run `uv run pytest tests/test_bot_commands.py -v` — must pass before task 5

### Task 5: Verify acceptance criteria

- [ ] Manual reasoning check: TOC button for private chat generates a `tg://openmessage` URL
  button, not a `callback_data` button
- [ ] Manual reasoning check: clicking such a URL in Telegram opens the original message, no copy
  is created
- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Run type checker: `uv run mypy src/`
- [ ] Run linter: `uv tool run ruff check src/ tests/`
- [ ] Verify coverage still meets threshold: `uv run pytest tests/ --cov=src --cov-report=term`

### Task 6: Update memory

- [ ] Update `MEMORY.md` to note that private chat TOC buttons now use `tg://openmessage` URL
  buttons (not callback_data)
- [ ] Move this plan to `docs/plans/completed/`
