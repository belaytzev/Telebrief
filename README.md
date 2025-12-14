# Telebrief

**Automated Telegram Digest Generator powered by GPT-5-nano**

Telebrief collects messages from your Telegram channels (in any language), generates AI-powered summaries, and delivers beautiful daily digests **in Russian** directly to your Telegram account.

---

## Features

✅ **Multi-language Support** - Reads channels in ANY language (English, Russian, Ukrainian, Chinese, etc.)
✅ **Russian Output Only** - All summaries generated in Russian regardless of source language
✅ **GPT-5-nano Powered** - High-quality AI summarization with ultra-low cost ($0.05/$0.40 per 1M tokens)
✅ **Scheduled & On-Demand** - Daily automatic digests + instant generation via bot commands
✅ **Private Channel Support** - Access your private chats and channels
✅ **Smart Formatting** - Markdown with emojis, bullet points, and clickable message links
✅ **Secure** - Single-user only, credentials stored safely

---

## Quick Start

### Prerequisites

Before you begin, gather these credentials:

1. **Telegram App Credentials** (from https://my.telegram.org)
   - `api_id` and `api_hash`

2. **Telegram Bot Token** (from @BotFather on Telegram)
   - Create bot: `/newbot`

3. **OpenAI API Key** (from https://platform.openai.com)
   - Requires GPT-5-nano access

4. **Your Telegram User ID** (from @userinfobot on Telegram)

### Installation

```bash
# 1. Clone or download the project
cd telebrief

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env with your API credentials
nano .env

# 5. Configure channels
nano config.yaml
# Add your Telegram channels

# 6. Run the application
python main.py
```

### First Run

On first run, Telethon will ask for phone verification:

```
Please enter your phone (or bot token): +1234567890
Please enter the code you received: 12345
```

This creates a session file that persists authentication.

---

## Configuration

### config.yaml

Add your Telegram channels to monitor:

```yaml
channels:
  - id: "@techcrunch"
    name: "TechCrunch"
  - id: "@cryptonews"
    name: "Crypto News"
  - id: -1001234567890  # Private chat ID
    name: "Private Group"

settings:
  schedule_time: "08:00"  # UTC time for daily digest
  timezone: "UTC"
  openai_model: "gpt-5-nano"
  target_user_id: 123456789  # Your Telegram ID
```

**Finding Channel IDs:**

**For public channels:**
- Use `@channelname` format (e.g., `@techcrunch`)

**For private channels/groups:**
1. Forward a message from the channel to [@RawDataBot](https://t.me/RawDataBot)
2. Copy the full chat ID from the response (should start with `-100`)
3. Example: If bot shows `"id": -1001234567890`, use exactly that number

**IMPORTANT Channel ID Format:**
- ✅ Correct: `id: -1001234567890` (integer with `-100` prefix, no quotes)
- ❌ Wrong: `id: "-1001234567890"` (quoted)
- ❌ Wrong: `id: -1234567890` (missing `-100` prefix)

**Note:** Channels, supergroups, and megagroups always have IDs starting with `-100`. Small group chats have shorter IDs without this prefix.

### .env

```bash
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash_here
TELEGRAM_BOT_TOKEN=123456789:ABC...
OPENAI_API_KEY=sk-proj-...
LOG_LEVEL=INFO
```

---

## Usage

### Automatic Mode

Once running, Telebrief automatically generates and sends digests daily at your configured time (default: 8 AM UTC).

### Bot Commands

Open Telegram and message your bot:

| Command | Description |
|---------|-------------|
| `/digest` | Generate digest for last 24 hours instantly |
| `/status` | Show configuration and next scheduled run |
| `/help` | Display help message |

### Running as Service (Linux VPS)

Create systemd service:

```bash
sudo nano /etc/systemd/system/telebrief.service
```

```ini
[Unit]
Description=Telebrief Digest Generator
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/telebrief
Environment=PATH=/home/YOUR_USERNAME/telebrief/venv/bin
ExecStart=/home/YOUR_USERNAME/telebrief/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telebrief
sudo systemctl start telebrief
sudo systemctl status telebrief
```

---

## Example Output

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

---

## Cost Estimation

**GPT-5-nano Pricing** (Default):
- Input: $0.050 per 1M tokens
- Output: $0.400 per 1M tokens

**Estimated costs** (~20 channels, medium activity):

| Model | Daily Cost | Monthly Cost |
|-------|-----------|--------------|
| **GPT-5-nano** (default) | ~$0.01/day | **~$0.30/month** ⭐ |

**Example calculation:**
- Input: ~100K tokens/day (reading messages)
- Output: ~10K tokens/day (summaries)
- Cost: (100K × $0.05 + 10K × $0.40) / 1M = **$0.009/day** = **$0.27/month**

💡 **Ultra-affordable pricing - perfect for personal daily digests!**

**GPT-5-nano API Differences:**
- ❌ Does NOT support: `temperature`, `top_p`, `logprobs`, `max_completion_tokens`
- ✅ Uses instead: `max_output_tokens` (for token limits)
- ✅ Optional: `reasoning.effort` (none/low/medium/high) and `text.verbosity` (low/medium/high)
- These differences are automatically handled by the app

Configure settings in `config.yaml` to customize your digest generation.

---

## Troubleshooting

### Digest not received?

```bash
# Check logs
tail -f logs/telebrief.log

# Check service status (if using systemd)
sudo systemctl status telebrief

# Restart
sudo systemctl restart telebrief
```

### Bot not responding?

- Verify bot token in `.env`
- Check your user ID matches `target_user_id` in config
- Ensure bot privacy is disabled (via @BotFather: `/setprivacy`)

### Channel access errors?

**Error: "Cannot get entity by phone number as a bot"**
- Make sure numeric channel IDs don't have quotes: `id: -1001234567890` not `id: "-1001234567890"`

**Error: "Invalid object ID for a chat... megagroups are channels"**
- Channel ID is missing the `-100` prefix
- Use @RawDataBot to get the complete ID (e.g., `-1001234567890`, not `-1234567890`)
- Channels/supergroups/megagroups must have IDs starting with `-100`

**Error: "Could not find the input entity for PeerChannel"**
- **You must join the channel** with your Telegram account (the same account that authenticated the app)
- Open Telegram and search for the channel, then click "Join"
- After joining, restart the application
- Verify the channel ID is correct using @RawDataBot

**Error: Empty AI summaries / no content in digest**
- **Root cause**: GPT-5 models require `max_output_tokens` instead of `max_completion_tokens`
- The app has been updated to use the correct parameter
- If you see empty digests, update to the latest version

**Error: "Unsupported parameter: 'temperature'" or 'max_completion_tokens'**
- GPT-5 models (gpt-5-nano, gpt-5-mini, gpt-5.1) have different API parameters
- They do NOT support: `temperature`, `top_p`, `logprobs`, `max_completion_tokens`
- They use: `max_output_tokens`, optional `reasoning.effort`, `text.verbosity`
- The app has been updated to use correct parameters

**Error: "The API access for bot users is restricted"**
- Some groups disable message history access even for members
- Try using the channel's direct link or check group settings
- Verify you're actually a member of the group/channel

**Error: "Channel is private or not accessible"**
- Ensure you've joined the channel/group with your Telegram account
- For private channels, you must be a member to access messages
- Check that the channel ID is correct (use @RawDataBot)

### Authentication errors?

```bash
# Remove session and re-authenticate
rm sessions/user.session
python main.py
# Follow phone verification prompts
```

### Import errors?

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

---

## Project Structure

```
telebrief/
├── main.py                 # Application entry point
├── config.yaml            # Channel configuration
├── .env                   # API credentials (not in git)
├── requirements.txt       # Python dependencies
├── SPECIFICATION.md       # Technical specification
├── README.md              # This file
├── src/
│   ├── config_loader.py   # Configuration management
│   ├── collector.py       # Message collection (Telethon)
│   ├── summarizer.py      # AI summarization (OpenAI)
│   ├── formatter.py       # Markdown formatting
│   ├── sender.py          # Bot message delivery
│   ├── core.py            # Core digest generation
│   ├── scheduler.py       # Daily scheduling
│   ├── bot_commands.py    # Bot command handlers
│   └── utils.py           # Utility functions
├── logs/
│   └── telebrief.log      # Application logs
└── sessions/
    └── user.session       # Telegram session (not in git)
```

---

## Security

- **Credentials**: Stored in `.env` (never commit to git)
- **Session files**: Contain auth tokens (gitignored, back them up securely)
- **User verification**: Bot only responds to configured `target_user_id`
- **Private channels**: Requires user credentials to access

---

## Development & Testing

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests with coverage
make test

# Run linters
make lint

# Auto-format code
make format
```

### Available Make Commands

```bash
make help          # Show all available commands
make install-dev   # Install dev dependencies
make test          # Run tests with coverage
make test-fast     # Run tests without coverage
make lint          # Run all linters (black, flake8, mypy, pylint, vulture)
make format        # Auto-format code
make clean         # Remove build artifacts
make pre-commit    # Install pre-commit hooks
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Code Quality

The project uses:
- **pytest** for testing (45%+ coverage required)
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking
- **Pylint** for code analysis (8.0+ rating required)
- **Vulture** for detecting unused code

#### Detecting Unused Code

The project uses Vulture to automatically detect unused functions, classes, variables, and imports:

```bash
# Run as part of full linting
make lint

# Run vulture separately
vulture src vulture_whitelist.py --min-confidence 80
```

**Whitelist Configuration**: `vulture_whitelist.py` contains intentionally unused code patterns (e.g., main() functions, required API signatures). Add patterns here to avoid false positives.

### CI/CD

GitHub Actions runs on every push/PR:
- Linting (Black, Flake8, MyPy, Pylint, Vulture)
- Tests (Python 3.10, 3.11, 3.12)
- Security scans (Bandit, Safety)
- Build verification

See [TESTING.md](TESTING.md) for comprehensive testing guide.

---

## FAQ

**Q: Can I use this for non-Russian output?**
A: Yes! Edit the prompts in `src/summarizer.py` to change output language.

**Q: How many channels can I monitor?**
A: Tested up to 50 channels. Performance depends on message volume.

**Q: Can multiple users receive digests?**
A: Currently single-user only. Multi-user support would require database and additional auth logic.

**Q: Does it work with group chats?**
A: Yes! Add group chat IDs to `config.yaml` the same way as channels.

**Q: Can I customize the digest format?**
A: Yes! Edit `src/formatter.py` to change Markdown structure, emojis, and sections.

---

## Credits

**Built with:**
- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram User API
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Bot API
- [OpenAI API](https://openai.com) - GPT-5-nano Summarization
- [APScheduler](https://github.com/agronholm/apscheduler) - Task Scheduling

---

**Happy digesting! 📊🤖**
