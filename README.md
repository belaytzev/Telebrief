<div align="center">
  <img src="misc/logo.png" alt="Telebrief Logo" width="200"/>

  # Telebrief

  **AI digests of your Telegram channels, delivered by your own bot**

  [![CI](https://github.com/belaytzev/Telebrief/actions/workflows/ci.yml/badge.svg)](https://github.com/belaytzev/Telebrief/actions/workflows/ci.yml)
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Docker: amd64 | arm64](https://img.shields.io/badge/docker-amd64%20%7C%20arm64-2496ED?logo=docker&logoColor=white)](https://github.com/belaytzev/Telebrief/pkgs/container/telebrief)
  [![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)
  [![Telebrief MCP server – quality and maintenance score on Glama](https://glama.ai/mcp/servers/belaytzev/Telebrief/badges/score.svg)](https://glama.ai/mcp/servers/belaytzev/Telebrief)
  [![Listed on mcpservers.org](https://mcpservers.org/badge.svg)](https://mcpservers.org/servers/belaytzev/telebrief)

  Telebrief reads your Telegram channels, in any language, summarizes them with OpenAI, Anthropic or a local Ollama model, and sends you a daily digest through your own Telegram bot. The digest can be grouped by channel or by topics the AI picks out. It is written in English, Russian, Spanish, German or French (Russian by default).

  <br/>

  <img src="misc/overview.png" alt="How Telebrief works: Telegram channels are collected, summarized by OpenAI, Anthropic or Ollama, and delivered as a daily digest to your bot or to AI agents over MCP. Right side: a sample digest with an overview and per-channel bullet points." width="100%"/>
</div>

## Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Bot commands](#bot-commands)
- [Example output](#example-output): [channel mode](#channel-mode-digest_mode-channel-default), [topic mode](#topic-mode-digest_mode-digest), [deduplication](#cross-channel-deduplication-dedup_topics)
- [Per-channel configuration](#per-channel-configuration): [lookback window](#per-channel-lookback-window-lookback_hours), [AI instructions](#per-channel-ai-instructions-prompt_extra)
- [Persistent storage](#persistent-storage): [SQLite](#sqlite-default-backend), [PostgreSQL](#postgresql-optional-backend), [schema](#schema)
- [Extensibility](#extensibility): [filters](#filters), [prompts](#prompts), [group binding](#group-binding), [storage queries](#storage-queries)
- [MCP server](#mcp-server): [enabling](#enabling-it), [stdio mode](#stdio-mode), [tools](#tools), [single channel](#reading-a-single-channel), [searching](#searching), [security](#security)
- [Development and testing](#development-and-testing)
- [FAQ](#faq)
- [Contributing](#contributing) · [License](#license) · [Credits](#credits)

## Features

- Reads channels in any language: English, Russian, Ukrainian, Chinese and so on.
- Writes summaries, labels and bot messages in English, Russian, Spanish, German or French (Russian by default).
- Summarizes with OpenAI (including GPT-6 Luna, Sol and Astra), Anthropic, or a local Ollama model.
- Sends a digest on a daily schedule, or right away when you ask the bot.
- Reads your private chats and channels, not only public ones.
- Groups the digest by channel (default) or by topics such as News, Events and Sport.
- Formats the digest as Markdown with emojis, bullet points and clickable channel links.
- Splits a digest longer than Telegram's 4096-character limit into several messages instead of cutting it off.
- Runs on your own server for a single user. Your session, API keys and messages stay there.
- Deletes old digest messages automatically.
- Can serve digests over an optional MCP endpoint, so AI agents get them without reading Telegram.

## Prerequisites

You need four things:

1. **Docker**: [install Docker](https://docs.docker.com/get-docker/).

2. **Telegram app credentials** (`api_id` and `api_hash`) from [my.telegram.org](https://my.telegram.org).
   - If the form at [my.telegram.org/apps](https://my.telegram.org/apps) only shows `ERROR`, Telegram rejected the request; Telebrief is not involved yet. These usually help:
     - Use a unique, random alphanumeric App title and Short name (Short name: 5 to 32 letters or digits, no spaces).
     - Turn off VPN, proxy and ad-blocking extensions; try a private window or another browser.
     - Switch networks, for example to mobile data instead of Wi-Fi.
     - Submit the form a few more times; the check fails intermittently.
   - If nothing works, contact [Telegram support](https://telegram.org/support). Never enter your login code on third-party sites that offer to create an app for you.

3. **A Telegram bot token**. Send `/newbot` to [@BotFather](https://t.me/BotFather) and save the token it gives you.

4. **An AI provider**, one of:
   - OpenAI: API key from [platform.openai.com](https://platform.openai.com)
   - Anthropic: API key from [console.anthropic.com](https://console.anthropic.com)
   - Ollama: no key, [install it locally](https://ollama.com)

## Quick start

You don't need to clone the repository or install Python. In an empty directory, run the setup wizard:

```bash
mkdir telebrief && cd telebrief
docker run --rm -it --user "$(id -u):$(id -g)" -v "$PWD":/setup \
  ghcr.io/belaytzev/telebrief python main.py init /setup
```

The wizard logs into your Telegram account (phone, code, 2FA), checks the bot token, lets you pick channels from your dialogs by number, and writes `.env`, `config.yaml`, `docker-compose.yml` and `sessions/user.session`. It takes your user ID from the login.

Then press **Start** in your bot's chat and launch the service:

```bash
docker compose up -d
docker compose logs -f telebrief
```

Send `/digest` to the bot to get the first digest right away. You can re-run the wizard at any time: it reuses the existing session and asks before overwriting files.

To update to the latest release:

```bash
docker compose pull && docker compose up -d
```

Each release is published to GitHub Container Registry with the tags `latest`, `X.Y` (minor) and `X.Y.Z` (patch). To build from source, replace the `image:` line in `docker-compose.yml` with `build: .`. Settings the wizard doesn't ask about are listed in [`config.yaml.example`](config.yaml.example).

## Bot commands

Message your bot in Telegram:

| Command | Description |
|---------|-------------|
| `/start` | Same as `/help` |
| `/help` | Lists all commands |
| `/digest` | Builds and sends a digest for the last 24 hours, using the configured `digest_mode` |
| `/status` | Shows the AI provider and model, the number of channels, auto-cleanup and the next scheduled run |
| `/cleanup` | Deletes old digest messages now |

## Example output

`digest_mode` in `config.yaml` picks one of two layouts.

### Channel mode (`digest_mode: "channel"`, default)

Summaries are grouped by source channel, each with a link to the channel:

```markdown
# 📊 Daily Digest - 02 May 2026

## 🎯 Brief Overview

A busy day in tech: a major framework release and a security patch worth
applying. Markets closed higher, and there is a self-hosting meetup this Friday.

---

## 💻 Tech News · [Open channel →](https://t.me/technews)

- 🚀 **Framework 2.0 released**: faster builds, new plugin API
- 🔐 **Security advisory**: patch for a popular web server

## 💰 Markets · [Open channel →](https://t.me/markets)

- 📈 **Stocks close higher**: tech shares lead the rally
- 🏦 **Rate decision**: central bank holds steady

---
📈 **Statistics**: 3 channels, 214 messages processed
```

The AI writes each channel's bullet points from the prompt, so their layout differs a little between providers and models.

### Topic mode (`digest_mode: "digest"`)

Summaries are grouped by topic. You define the topics in `config.yaml`:

```yaml
digest_mode: "digest"
digest_groups:
  - name: "Events"
    description: "Conferences, meetups, releases, launches, announcements"
  - name: "News"
    description: "Politics, economy, world affairs, breaking news"
  - name: "Sport"
    description: "Sports results, transfers, tournaments, matches"
```

Messages that fit none of them go into an automatic "Other" group.

> All labels (header, statistics, bot commands) follow `output_language`. The example above is in `English`; the other values are `Russian` (default), `Spanish`, `German` and `French`.

### Cross-channel deduplication (`dedup_topics`)

When several channels cover the same event, the digest normally gets one bullet point per channel. With `dedup_topics` on, the AI keeps the most informative description and lists all the sources on it:

```yaml
settings:
  digest_mode: "digest"
  dedup_topics: true        # default: false
  digest_groups:
    - name: "Tech"
      description: "Technology news and releases"
```

If `TechCrunch` and `HackerNews` both report the same product launch, the digest shows one bullet point with `source: "TechCrunch, HackerNews"` instead of two.

> **Note:** `dedup_topics` does nothing in `digest_mode: "channel"`, because deduplication happens while messages are grouped by topic.

## Per-channel configuration

Besides the required `id` and `name`, each channel entry takes two optional overrides.

### Per-channel lookback window (`lookback_hours`)

Overrides the global `settings.lookback_hours` for one channel. Give a quiet channel a wider window, or a busy one a narrower one.

```yaml
channels:
  - id: "@breaking_news"
    name: "Breaking News"
    # no lookback_hours — uses the global settings.lookback_hours

  - id: "@weekly_digest"
    name: "Weekly Newsletter"
    lookback_hours: 168   # look back 7 days for this channel only

  - id: -1001234567890
    name: "High Volume Channel"
    lookback_hours: 6     # only last 6 hours for this channel
```

`lookback_hours` must be a positive integer. If it is missing or `null`, the global value applies.

### Per-channel AI instructions (`prompt_extra`)

Adds your own instructions to the system prompt for one channel, to steer tone, focus or format.

```yaml
channels:
  - id: "@cryptonews"
    name: "Crypto News"
    prompt_extra: "Focus only on price movements and regulatory news. Ignore opinion pieces."

  - id: "@jobboard"
    name: "Job Board"
    prompt_extra: "Extract only senior engineering roles. Format as a list: Role — Company — Link."
```

The text is appended to the channel's system prompt as is. Leave the field empty or omit it to keep the standard prompt.

## Persistent storage

Telebrief doesn't keep raw messages by default. If you want the history, for your own queries or other LLM tools, turn on storage in `config.yaml` and every collected message is written to a database.

### SQLite (default backend)

Needs no setup; messages go to a local SQLite file.

```yaml
storage:
  enabled: true
  backend: sqlite
  path: data/messages.db   # relative to project root
```

In Docker, `docker-compose.yml` already mounts `data/` as a volume, so the database survives container restarts.

### PostgreSQL (optional backend)

Use PostgreSQL when Telebrief runs on several hosts or when other programs read the messages at the same time.

```yaml
storage:
  enabled: true
  backend: postgres
  url: "postgresql://user:pass@host:5432/dbname"
```

`asyncpg` is already in the Docker image and in the standard dependencies (`uv sync`), so there is nothing extra to install.

### Schema

Both backends create the same table and index on first run; there are no migrations to apply by hand.

| Column | Type | Description |
|--------|------|-------------|
| `channel_name` | text | Channel name from your config |
| `sender` | text | Message author |
| `text` | text | Message body |
| `timestamp` | text / timestamptz | Message timestamp |
| `link` | text | Telegram message link |
| `has_media` | bool / integer | Whether the message has media |
| `media_type` | text | Media type string |
| `collected_at` | text / timestamptz | When the row was inserted |

**Note**: storage only appends. If `lookback_hours` windows of two runs overlap, messages from the overlap are stored twice.

## Extensibility

Four parts of the pipeline can be swapped or extended from `config.yaml` without touching the core code. All the fields below are optional, and existing configs keep working.

### Filters

Filters run after collection and before storage and summarization. A message a filter drops never reaches the AI or the database.

The built-in filters are in `src/extensions/filters.py`:

| Filter | Purpose |
|--------|---------|
| `KeywordFilter` | Keep or drop messages containing a keyword (case-insensitive) |
| `RegexFilter` | Keep or drop messages matching a regex pattern |
| `MinLengthFilter` | Drop messages shorter than a set number of characters |

Set the global chain under `settings.filters`. Each entry needs a `class_path` (dotted import path) and can take a `config` dict, passed to the constructor as keyword arguments:

```yaml
settings:
  filters:
    - class_path: src.extensions.filters.KeywordFilter
      config:
        include: ["job", "hiring", "remote"]
        exclude: ["nsfw"]
    - class_path: src.extensions.filters.MinLengthFilter
      config:
        min_chars: 30
```

To change the chain for one channel, add `filters:` to that channel's entry. `filters: []` turns filtering off for the channel; any other list replaces the global chain for it:

```yaml
channels:
  - id: "@jobboard"
    name: "Job Board"
    filters:
      - class_path: src.extensions.filters.RegexFilter
        config:
          pattern: "senior|staff|principal"
          mode: "include"
```

A custom filter implements the `MessageFilter` Protocol:

```python
from __future__ import annotations
from src.extensions.filters import MessageFilter
from src.config_loader import ChannelConfig
from src.collector import Message

class MyFilter:
    name = "my_filter"

    def __init__(self, custom_param: str = "") -> None:
        self.custom_param = custom_param

    async def filter(self, channel: ChannelConfig, messages: list[Message]) -> list[Message]:
        return [m for m in messages if self.custom_param in (m.text or "")]
```

Then reference it in `config.yaml`:

```yaml
settings:
  filters:
    - class_path: mypackage.mymodule.MyFilter
      config:
        custom_param: "important"
```

### Prompts

The base prompt template is `src/prompts/base_summary.txt`. You can point to another template file or plug in your own `PromptComposer` class.

```yaml
prompts:
  base_template: src/prompts/base_summary.txt  # path to template file
  composer: ""                                  # empty = built-in DefaultComposer
```

The built-in `DefaultComposer` builds the system prompt in this order, skipping empty parts:

```text
base template (with {language} substituted)
  + group.prompt_extra  (if channel belongs to a group with prompt_extra set)
  + channel.prompt_extra  (if non-empty)
```

For a custom composer, implement the `PromptComposer` Protocol and set `composer` to its dotted path:

```python
from src.config_loader import ChannelConfig, DigestGroupConfig
from src.extensions.prompts import PromptComposer

class MyComposer:
    def __init__(self, base_template: str, language: str) -> None:
        self._base = base_template
        self._language = language

    def compose(self, channel: ChannelConfig, group: DigestGroupConfig | None) -> str:
        return f"{self._base}\nRespond in {self._language}."
```

> **Note:** the constructor must take `(base_template: str, language: str)` as its first two positional arguments. Otherwise Telebrief stops at startup with a `TypeError` that says what is wrong.

```yaml
prompts:
  composer: mypackage.mymodule.MyComposer
```

### Group binding

A channel can be bound to a `digest_groups` entry. The group's `prompt_extra` then goes into the prompt of every channel in the group, before the channel's own `prompt_extra`.

```yaml
settings:
  digest_groups:
    - name: "Jobs"
      description: "Job listings and hiring announcements"
      prompt_extra: "Extract only role title, company, and link. Format as a list."

channels:
  - id: "@techleads_jobs"
    name: "Tech Jobs"
    group: Jobs          # must match a digest_groups name or "Other"
    prompt_extra: "Focus on senior and staff-level positions only."
```

A channel without `group` (or with `group: null`) gets the base template and its own `prompt_extra` only.

### Storage queries

With storage on (`storage.enabled: true`), external tools can read messages through `StorageBackend.query_messages`:

```python
from src.storage import SQLiteBackend
from datetime import datetime, timezone

backend = SQLiteBackend("data/messages.db")
await backend.initialize()

messages = await backend.query_messages(
    channel_name="TechCrunch",  # the configured channels[*].name (NOT the @id)
    since=datetime(2026, 4, 1, tzinfo=timezone.utc),
    until=datetime(2026, 4, 30, tzinfo=timezone.utc),
    limit=500,
)
```

All parameters are optional. `channel_name` is the readable `channels[*].name` from `config.yaml`, the same value written to the `channel_name` column at collection time; leave it out to query all channels. If you rename a channel in the config, new rows get the new name and old rows keep the old one. Results come newest first, at most `limit` of them (1000 by default, minimum 1).

## MCP server

Telebrief can serve its digests over the [Model Context Protocol](https://modelcontextprotocol.io), so an MCP client such as Claude Code can ask for a digest directly instead of reading it in Telegram.

The server runs **inside the Telebrief process** and shares the Telegram session, the configuration and the generation lock with the scheduler and the bot. It returns exactly the digest Telegram gets, byte for byte, including topic grouping and deduplication.

### Enabling it

```yaml
mcp:
  enabled: true
  host: "127.0.0.1"
  port: 8765
  path: "/mcp"
```

Then register it with your client:

```bash
claude mcp add --transport http telebrief http://127.0.0.1:8765/mcp
```

### Stdio mode

`python main.py mcp` serves the same tools over stdio, without the bot and the scheduler, for clients that start the server themselves. It reads the same `config.yaml`, `.env` and session and connects to Telegram only when a tool is called. Don't run it next to the main service on the same session file; if Telebrief is already running, use the HTTP endpoint above.

### Tools

| Tool | Arguments | Behaviour |
|------|-----------|-----------|
| `get_digest` | `hours` (1–168, default 24) | Builds a fresh digest. Takes 20 to 90 seconds and spends AI provider tokens. `hours=168` gives a weekly digest. |
| `get_last_digest` | — | Returns the latest digest from the cache with the time it was built. Instant, costs nothing. |
| `get_channel_messages` | `channel`, `hours` (1–168, default 24), `limit` (1–500, default 200) | Returns the raw messages of one channel, without summarizing. Spends no AI tokens. |
| `search_messages` | `query`, `channel` (optional), `days` (1–365, default 30), `limit` (1–100, default 30) | Searches all configured channels, or one, newest first. Spends no AI tokens. |

Every successful digest, whether started by the schedule, the bot or MCP, is saved to `data/last_digest.json`, so `get_last_digest` returns the same digest Telegram received.

Only one digest is built at a time. If the scheduler is already building one, an MCP call waits for it instead of opening a second Telegram session.

### Reading a single channel

`get_channel_messages` shows what was actually posted in a channel, where a digest gives you the AI summary.

`channel` takes either the readable `channels[*].name` or the `channels[*].id` (`@username` or numeric) from `config.yaml`, case-insensitively. An unknown value returns an error with the list of configured channel names, so you don't need a separate call to find them.

The tool reads from persistent storage when storage is on and has messages for the requested window; otherwise it reads Telegram live. The response header says which one it used:

```text
channel: AI News (from storage, 42 msgs, last 24h)

[2026-08-07T09:12:04+00:00] Alice
OpenAI released a new model...
https://t.me/ainews/1234

[2026-08-07T10:30:11+00:00] Bob
[photo] Benchmark chart
https://t.me/ainews/1235
```

Messages come in chronological order; `limit` keeps the newest and drops the oldest. The live read takes the same lock as digest generation and applies the channel's [filters](#filters), so both paths return the same messages.

It differs from digest generation in two ways, on purpose:

- `channels[*].lookback_hours` is ignored; the tool uses the `hours` the caller asked for.
- Messages that are only media come back as their placeholder text (`[photo]`, `[video]`), the same as in storage.

### Searching

`search_messages` finds where and when something was mentioned. It uses Telegram's own search, so it covers each channel's full history, not only what Telebrief collected, and it works without persistent storage. It matches words, as the Telegram app does, not substrings or regexes.

Each call sends one Telegram request per channel searched, under the same lock as digest generation, so pass `channel` when you know where to look. Channel [filters](#filters) don't apply to search results. If a channel can't be searched (you left it, it's private, or Telegram rate-limited the request), the other channels still return results and the response header names the ones that failed:

```text
search: 'kubernetes' (2 matches, last 30 days)
search failed in: Private Group

[2026-09-26T14:02:11+00:00] Tech News · Alice
Kubernetes 1.34 is out...
https://t.me/technews/812
```

### Security

**The MCP server has no authentication.** It relies on listening only on loopback, where the SDK also turns on DNS-rebinding protection. Anyone who can reach the port can start digest generation and read your channel summaries.

Keep `host` at `127.0.0.1`; Telebrief logs a warning at startup if you bind to anything else. In Docker, publish the port as `127.0.0.1:8765:8765`, not on all interfaces. If you do need remote access, put it behind a firewall or a reverse proxy with authentication.

## Development and testing

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14+. Setup, the full set of checks, code style and the PR process are described in the [contributing guide](CONTRIBUTING.md).

### Running tests

```bash
uv sync --extra dev
uv run pytest tests/ -v
uv run mypy src/
```

## FAQ

**Q: Which output languages are supported?**
A: English, Russian (default), Spanish, German and French, set with `output_language`. The channels themselves can be in any language.

**Q: How many channels can I follow?**
A: There is no hard limit. Each digest reads up to `max_messages_per_channel` messages per channel (500 by default), so run time and AI cost grow with the number of active channels.

**Q: Can several people receive digests?**
A: No. Telebrief is built for one user: one Telegram account, one recipient.

**Q: Does it work with group chats?**
A: Yes. The setup wizard lists your groups along with channels, or you can add a group's ID to `config.yaml` like any channel.

**Q: Is my Telegram account at risk?**
A: Telebrief logs in as you through the Telegram user API (Telethon) and only reads messages. Still, it is a user session, not a bot, so Telegram's usual rules for third-party clients apply. The session file in `sessions/` gives full access to your account, so keep it private.

**Q: How much does it cost to run?**
A: Only the AI provider's tokens, which depend on the model and on how much your channels post. A nano or mini model keeps the cost low; with Ollama it's free.

**Q: Can I use a local AI model?**
A: Yes. Set `ai_provider: "ollama"` in `config.yaml` and run [Ollama](https://ollama.com). From Docker, set `ollama_base_url` to `http://host.docker.internal:11434`; on Linux, also add `extra_hosts: ["host.docker.internal:host-gateway"]` to `docker-compose.yml`.

**Q: Can I change the digest format?**
A: The layout is defined in `src/formatter.py`, so changing it means [building the image from source](#quick-start). Per-channel `prompt_extra` and custom [prompts](#prompts) change what the AI writes without touching the code.

## Contributing

Bug reports, feature requests, documentation fixes, new filters, AI providers, storage backends and translations are all welcome.

- The [contributing guide](CONTRIBUTING.md) covers development setup, code style and the PR process.
- The project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
- Please report security issues privately, as described in the [security policy](SECURITY.md).

## License

[MIT](LICENSE).

## Credits

Built with:

- [Telethon](https://github.com/LonamiWebs/Telethon): Telegram user API
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot): Bot API
- [OpenAI API](https://openai.com): summarization with the OpenAI provider
- [Ollama](https://ollama.com): local summarization
- [Anthropic API](https://anthropic.com): summarization with the Anthropic provider
- [APScheduler](https://github.com/agronholm/apscheduler): task scheduling
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk): MCP server
