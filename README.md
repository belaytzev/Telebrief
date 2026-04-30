<div align="center">
  <img src="misc/logo.png" alt="Telebrief Logo" width="200"/>

  # Telebrief

  **Automated Telegram Digest Generator powered by AI**

  Telebrief collects messages from your Telegram channels (in any language), generates AI-powered summaries, and delivers beautiful daily digests directly to your Telegram account. Group digests by channel or by **AI-detected topics**. Supports multiple AI providers: **OpenAI**, **Ollama** (local), and **Anthropic**. Output language is configurable (default: Russian).
</div>

---

## ✨ Features

- 🌐 **Multi-language Support** - Reads channels in ANY language (English, Russian, Ukrainian, Chinese, etc.)
- 🌍 **Configurable Output Language** - All UI labels, summaries, and bot messages in any language (default: Russian)
- 🤖 **Multi-Provider AI** - Supports OpenAI, Ollama (local), and Anthropic for summarization
- ⏰ **Scheduled & On-Demand** - Daily automatic digests + instant generation via bot commands
- 🔒 **Private Channel Support** - Access your private chats and channels
- 📑 **Digest Modes** - Group by channel (default) or by AI-detected topics like News, Events, Sport
- 🎨 **Smart Formatting** - Markdown with emojis, bullet points, and clickable channel links
- 📨 **Long Message Splitting** - Digests that exceed Telegram's 4096-character limit are automatically split into sequential messages instead of being truncated
- 🔐 **Secure** - Single-user only, credentials stored safely
- 🧹 **Auto-cleanup** - Automatically removes old digest messages

---

## 📋 Prerequisites

Before you begin, you'll need:

1. **Python 3.14+** - [Download Python](https://www.python.org/downloads/)

2. **Telegram App Credentials** - [Get from my.telegram.org](https://my.telegram.org)
   - `api_id` and `api_hash`

3. **Telegram Bot Token** - Create via [@BotFather](https://t.me/BotFather)
   - Send `/newbot` to create a new bot
   - Save the bot token

4. **AI Provider API Key** (one of the following):
   - **OpenAI**: [Get from platform.openai.com](https://platform.openai.com)
   - **Anthropic**: [Get from console.anthropic.com](https://console.anthropic.com)
   - **Ollama**: No API key needed - [install locally](https://ollama.ai)

5. **Your Telegram User ID** - Get from [@userinfobot](https://t.me/userinfobot)
   - Send `/start` to get your ID

---

## 🐳 Docker Deployment

Telebrief can be run in Docker for easy deployment. **No Python installation required on host!**

The image is published to GitHub Container Registry on every release:

```bash
# Pull the latest image
docker pull ghcr.io/belaytzev/telebrief:latest
```

Available tags: `latest`, `X.Y` (minor), `X.Y.Z` (patch).

```bash
# 1. Create Telegram session (REQUIRED - one-time setup)
./create_session.sh

# 2. Start the service
docker compose up -d

# 3. View logs
docker compose logs -f telebrief
```

The `docker-compose.yml` uses the pre-built GHCR image by default, so no local build step is needed. If you want to build from source instead, replace the `image:` line with `build: .`.

**Important**: You must create the Telegram session file BEFORE running Docker. The script uses Docker itself, so no additional dependencies needed.

---

## 🤖 Bot Commands

Open Telegram and message your bot:

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and available commands |
| `/help` | Display help message with all commands |
| `/digest` | Generate and send digest for last 24 hours (uses configured `digest_mode`) |
| `/status` | Show configuration, next scheduled run, and system info |
| `/cleanup` | Manually delete old digest messages |

---

## 📊 Example Output

Telebrief supports two digest modes configured via `digest_mode` in `config.yaml`.

### Channel mode (`digest_mode: "channel"` — default)

Groups summaries by source channel with clickable channel links:

```markdown
# 📊 Ежедневный дайджест - 14 декабря 2025

## 🎯 Краткий обзор

Сегодня основные темы: запуск Python 3.13 с улучшениями производительности
обсуждался в нескольких технических каналах, криптовалютный рынок показал
высокую волатильность на фоне новостей о регулировании.

---

## 💻 TechCrunch

- 🚀 **Python 3.13 релиз**: Официально выпущена новая версия с JIT-компиляцией
- 🤖 **OpenAI анонсировала GPT-5**: Следующее поколение модели ожидается в Q1 2026
- 📱 **Apple vs EU**: Новые требования по interoperability

## 💰 Crypto News

- 📈 **Bitcoin волатильность**: Цена колебалась между $43K и $46K
- ⚠️ **SEC предупреждение**: Новая схема мошенничества
- 🔐 **Ethereum upgrade**: Успешно завершен тестнет

---
📈 **Статистика**: 20 каналов, 1,847 сообщений обработано
```

### Topic mode (`digest_mode: "digest"`)

Groups summaries by AI-detected topics. You define topic groups in `config.yaml`:

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

Messages that don't match any defined group are placed into an automatic "Other" category.

> All labels (header, statistics, bot commands) use the configured `output_language` — the examples above show the default Russian output.

---

## ⚙️ Per-Channel Configuration

Each channel entry supports two optional overrides in addition to the required `id` and `name` fields.

### `lookback_hours` — per-channel lookback window

Override the global `settings.lookback_hours` for a specific channel. Useful when some channels post infrequently and need a wider collection window, or when you want a tighter window for high-volume channels.

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

`lookback_hours` must be a positive integer. If omitted or set to `null`, the global value is used.

### `prompt_extra` — per-channel AI instructions

Append extra instructions to the AI system prompt when summarizing a specific channel. Use this to guide tone, focus, or format for channels that need special treatment.

```yaml
channels:
  - id: "@cryptonews"
    name: "Crypto News"
    prompt_extra: "Focus only on price movements and regulatory news. Ignore opinion pieces."

  - id: "@jobboard"
    name: "Job Board"
    prompt_extra: "Extract only senior engineering roles. Format as a list: Role — Company — Link."
```

`prompt_extra` is appended verbatim to the channel's summarization system prompt. Leave it empty (or omit the field) for standard behavior.

---

## 🗄️ Persistent Storage

By default, Telebrief generates digests on demand without storing raw messages. You can enable a persistent storage layer that saves every collected message to a database for historical access or external LLM workflows.

Storage is **disabled by default** and opt-in via `config.yaml`.

### SQLite (default backend)

No extra setup required. Messages are saved to a local SQLite file.

```yaml
storage:
  enabled: true
  backend: sqlite
  path: data/messages.db   # relative to project root
```

When running in Docker, the `data/` directory is already mounted as a volume in `docker-compose.yml`, so the database persists across container restarts.

### PostgreSQL (optional backend)

Use PostgreSQL for multi-host deployments or when you need concurrent read access to the message store.

```yaml
storage:
  enabled: true
  backend: postgres
  url: "postgresql://user:pass@host:5432/dbname"
```

`asyncpg` is included in the standard dependencies and is installed automatically by `uv sync`. No extra install step is needed.

### Schema

Both backends create the same logical schema on first run (table and index are created automatically — no manual migration needed):

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

**Note**: Storage is append-only. Overlapping `lookback_hours` windows across runs will produce duplicate rows for messages collected in both windows.

---

## 🛠️ Development & Testing

This project uses [uv](https://docs.astral.sh/uv/) for package management.

### Running Tests

```bash
# Install development dependencies
uv sync --extra dev

# Run all tests
uv run pytest tests/ -v

# Type checking
uv run mypy src/

# Linting
uv tool run ruff check src/ tests/

# Auto-format code
make format
```

---

## ❓ FAQ

**Q: Can I change the output language?**
A: Yes! Set `output_language` in `config.yaml` to any language (e.g., "English", "Spanish", "Chinese").

**Q: How many channels can I monitor?**
A: Tested up to 50 channels. Performance depends on message volume.

**Q: Can multiple users receive digests?**
A: Currently single-user only. Multi-user support would require database and additional auth logic.

**Q: Does it work with group chats?**
A: Yes! Add group chat IDs to `config.yaml` the same way as channels.

**Q: How do I switch to topic-based digests?**
A: Set `digest_mode: "digest"` in `config.yaml` and define your `digest_groups`. Each group has a `name` and `description` that guides the AI classification. An implicit "Other" group catches anything that doesn't match.

**Q: Can I customize the digest format?**
A: Yes! Edit `src/formatter.py` to change Markdown structure, emojis, and sections.

**Q: How much does it cost to run?**
A: With OpenAI GPT-5-nano: ~$0.30/month. With Ollama: free (runs locally). Anthropic pricing varies by model.

**Q: Can I use a local AI model?**
A: Yes! Set `ai_provider: "ollama"` in config.yaml and install [Ollama](https://ollama.ai) on your machine.

---


## 🙏 Credits

**Built with:**
- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram User API
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Bot API
- [OpenAI API](https://openai.com) - AI Summarization (OpenAI provider)
- [Ollama](https://ollama.ai) - Local AI Summarization
- [Anthropic API](https://anthropic.com) - AI Summarization (Anthropic provider)
- [APScheduler](https://github.com/agronholm/apscheduler) - Task Scheduling

---

<div align="center">
  <strong>Happy digesting! 📊🤖</strong>
</div>
