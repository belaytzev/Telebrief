# Digest Table of Contents with Navigation Buttons

## Overview

Add a Table of Contents (TOC) to the digest summary message. The TOC appears as inline keyboard buttons attached to the final summary message. Each button is labeled with the channel emoji + name and links directly to that channel's digest message in the chat, enabling quick navigation between channels.

## Context

- Files involved:
  - `src/sender.py` - `_send_channel_messages_loop()`, `send_channel_messages_with_tracking()`, `_send_summary_message()`
  - `src/formatter.py` - `DigestFormatter`, new `build_toc_keyboard()` helper
  - `src/core.py` - `generate_and_send_channel_digests()` (minimal change)
  - `tests/test_sender.py` - sender tests
  - `tests/test_formatter.py` - formatter tests
- Related patterns:
  - `_send_channel_messages_loop()` already returns `(sent_message_ids, success_count, failed_channels)` but only a flat list of IDs - no channel-to-ID mapping
  - `_send_summary_message()` sends the closing stats message - we add `reply_markup` here
  - `_pick_emoji()` in `formatter.py` - reuse this to label TOC buttons consistently
- Dependencies:
  - `telegram.InlineKeyboardMarkup`, `telegram.InlineKeyboardButton` (already part of python-telegram-bot, just not imported)

## Deep Link Strategy

The digest is sent to a private chat with the target user (positive user_id). Telegram deep links for private chat messages use:
- `tg://openmessage?user_id={chat_id}&message_id={msg_id}` for private chats (positive chat_id)
- `https://t.me/c/{abs_channel_id}/{msg_id}` for supergroups/channels (negative chat_id, strip the -100 prefix)

The link type is determined at send time by inspecting the sign of `user_id`.

## Development Approach

- **Testing approach**: TDD - write failing tests first, then implement
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Implementation Steps

### Task 1: Track channel-to-message-id mapping in `_send_channel_messages_loop`

**Files:**
- Modify: `src/sender.py`

- [x] Change `_send_channel_messages_loop` return type annotation from `tuple[list[int], int, list[str]]` to `tuple[list[int], list[tuple[str, int]], int, list[str]]`
- [x] Inside the loop, when a `message_id` is successfully obtained, also append `(channel_name, message_id)` to a new `channel_id_map: list[tuple[str, int]]` local list
- [x] Return `(sent_message_ids, channel_id_map, success_count, failed_channels)` at the end
- [x] Update `send_channel_messages_with_tracking` to unpack the new 4-tuple from `_send_channel_messages_loop`
- [x] Write tests in `tests/test_sender.py` verifying the returned `channel_id_map` contains correct `(channel_name, message_id)` pairs
- [x] Run `pytest tests/test_sender.py` - must pass before task 2

### Task 2: Add `build_toc_keyboard` to `DigestFormatter`

**Files:**
- Modify: `src/formatter.py`

- [x] Add import at top: `from telegram import InlineKeyboardMarkup, InlineKeyboardButton`
- [x] Add method `build_toc_keyboard(channel_id_map: list[tuple[str, int]], chat_id: int) -> InlineKeyboardMarkup`:
  - For each `(channel_name, message_id)` in `channel_id_map`:
    - Generate label: `f"{self._pick_emoji(channel_name)} {channel_name}"`
    - Generate URL: if `chat_id > 0` → `f"tg://openmessage?user_id={chat_id}&message_id={message_id}"`, else → `f"https://t.me/c/{str(abs(chat_id)).lstrip('100')}/{message_id}"` (strip the -100 prefix by removing leading "100" after taking abs)
    - Wait - for supergroup IDs like -1001234567890: `abs_id = str(abs(chat_id))[3:]` if `str(abs(chat_id)).startswith("100")` else `str(abs(chat_id))`
    - Create `InlineKeyboardButton(text=label, url=url)`
  - Arrange buttons 1 per row: `[[btn] for btn in buttons]`
  - Return `InlineKeyboardMarkup(keyboard)`
- [x] Write tests in `tests/test_formatter.py`:
  - Test that for positive `chat_id=123456`, URLs use `tg://openmessage?user_id=123456&message_id=...`
  - Test that for negative `chat_id=-1001234567890`, URLs use `https://t.me/c/1234567890/...`
  - Test that button labels include the emoji and channel name
  - Test that each button is on its own row
- [x] Run `pytest tests/test_formatter.py` - must pass before task 3

### Task 3: Attach TOC keyboard to summary message

**Files:**
- Modify: `src/sender.py`

- [x] Add import at top of sender.py: `from telegram import InlineKeyboardMarkup`
- [x] Modify `_send_summary_message` signature to accept an optional `reply_markup: Optional[InlineKeyboardMarkup] = None`
- [x] Pass `reply_markup=reply_markup` to `self.bot.send_message(...)` in `_send_summary_message`
- [x] Modify `send_channel_messages_with_tracking` to:
  - Accept new optional parameter `channel_id_map: Optional[list[tuple[str, int]]] = None`
  - If `summary_message` and `channel_id_map` and `success_count > 0`:
    - Build `keyboard = self.formatter.build_toc_keyboard(channel_id_map, user_id)` — requires `DigestFormatter` reference (see note below)
    - Pass `reply_markup=keyboard` to `_send_summary_message`
- [x] Since `DigestSender` doesn't currently hold a formatter reference, add `self.formatter = DigestFormatter(config)` to `DigestSender.__init__` (check if `DigestFormatter` needs any config - if it only needs logger/config, pass both)
- [x] Alternatively (simpler): accept `reply_markup: Optional[InlineKeyboardMarkup] = None` as a parameter to `send_channel_messages_with_tracking` and have the caller build the keyboard - this avoids adding formatter to sender. Choose whichever is cleaner based on code review.
- [x] Write tests in `tests/test_sender.py`:
  - Test that when `channel_id_map` is provided, `_send_summary_message` is called with a non-None `reply_markup`
  - Test that when `channel_id_map` is empty or None, `reply_markup` is None (no keyboard)
- [x] Run `pytest tests/test_sender.py` - must pass before task 4

### Task 4: Wire up channel_id_map in `core.py`

**Files:**
- Modify: `src/core.py`

- [ ] After `_send_channel_messages_loop` result is available (inside `send_channel_messages_with_tracking`), the `channel_id_map` is now returned automatically from Task 1 - so `core.py` requires NO changes if Task 3 uses the internal approach
- [ ] If the caller-builds-keyboard approach was chosen in Task 3, update `generate_and_send_channel_digests` in `core.py`:
  - Build keyboard with `formatter.build_toc_keyboard(channel_id_map, user_id)` before calling `send_channel_messages_with_tracking`
  - Pass `reply_markup=keyboard` to `send_channel_messages_with_tracking`
- [ ] Run `pytest tests/` - all tests must pass

### Task 5: Verify acceptance criteria

- [ ] Manual test: trigger `/digest` command and verify:
  - The final summary message has inline keyboard buttons
  - Each button is labeled `{emoji} {channel_name}`
  - Clicking a button navigates to that channel's digest message in the chat
- [ ] Run full test suite: `pytest tests/`
- [ ] Run linter: `ruff check src/ tests/` (or `flake8` if that's what the project uses)
- [ ] Verify no regression in cleanup functionality (message IDs still saved correctly)

### Task 6: Update documentation

- [ ] Update `README.md` if it describes the digest output format
- [ ] Move this plan to `docs/plans/completed/`
