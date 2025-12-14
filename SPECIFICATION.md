# Telebrief - Technical Specification (Final)

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Ready for Implementation

---

## Executive Summary

**Telebrief** is an automated Telegram digest generator that:
- Collects messages from ~20 Telegram channels/chats (public and private)
- Processes messages in ANY language (English, Russian, Ukrainian, etc.)
- Generates AI-powered summaries using GPT-4-turbo
- Delivers daily digests in **Russian language only** via Telegram bot
- Supports instant on-demand digest generation
- Runs unattended on Linux VPS

---

## Core Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Read messages from configured Telegram channels/chats | MUST |
| FR-2 | Support private channels (using user credentials) | MUST |
| FR-3 | Process messages in any language | MUST |
| FR-4 | Generate summaries in Russian language only | MUST |
| FR-5 | Daily scheduled execution at 8 AM UTC | MUST |
| FR-6 | Instant digest via `/digest` command | MUST |
| FR-7 | Bot status via `/status` command | MUST |
| FR-8 | Deliver digest to single authorized user only | MUST |
| FR-9 | Include clickable links to original messages | MUST |
| FR-10 | Markdown formatting with emojis | MUST |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Execution time | < 3 minutes for 2000 messages |
| NFR-2 | Reliability | 99% successful daily deliveries |
| NFR-3 | Security | Credentials encrypted, user whitelist |
| NFR-4 | Cost | ~$70/month (acceptable) |
| NFR-5 | Maintainability | Simple configuration, clear logging |

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│              Telebrief Application                  │
│                                                     │
│  ┌──────────────┐        ┌──────────────┐         │
│  │  Scheduler   │        │ Bot Handler  │         │
│  │  8 AM UTC    │        │  /digest     │         │
│  │              │        │  /status     │         │
│  └──────┬───────┘        └──────┬───────┘         │
│         │                       │                  │
│         └──────────┬────────────┘                  │
│                    ▼                                │
│         ┌─────────────────────┐                    │
│         │  generate_digest()  │ ← Core Logic      │
│         └──────────┬──────────┘                    │
└────────────────────┼─────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │Collector│  │Summarize│  │ Sender  │
   │Telethon │  │ OpenAI  │  │Bot API  │
   └─────────┘  └─────────┘  └─────────┘
```

### Component Breakdown

#### 1. Message Collector
- **Technology:** Telethon (Telegram User API)
- **Responsibility:** Fetch messages from configured channels
- **Input:** Channel list, time range (hours back)
- **Output:** List of message objects (text, sender, timestamp, link)
- **Features:**
  - Async parallel collection from multiple channels
  - Handle rate limiting with exponential backoff
  - Extract media descriptions ([Photo], [Video])
  - Generate clickable message links

#### 2. Summarizer
- **Technology:** OpenAI API (GPT-4-turbo)
- **Responsibility:** Generate summaries in Russian
- **Strategy:** Two-tier summarization
  1. Per-channel summaries (3-5 bullet points each)
  2. Combined overview (executive summary + details)
- **Prompts:** Explicitly instruct Russian output
- **Features:**
  - Handle multilingual input seamlessly
  - Maintain context and nuance
  - Identify key themes across channels

#### 3. Formatter
- **Responsibility:** Create Markdown digest
- **Output Format:**
  ```markdown
  # 📊 Ежедневный дайджест - [Date]

  ## 🎯 Краткий обзор
  [Executive summary in Russian]

  ---

  ## 📺 [Channel Name 1]
  - Key point 1 [🔗](link)
  - Key point 2 [🔗](link)

  ## 💼 [Channel Name 2]
  - Key point 1 [🔗](link)
  ...

  ---
  📈 **Статистика**: X каналов, Y сообщений обработано
  ```
- **Features:**
  - Emoji categorization (📰 news, 💬 discussions, 🔗 links)
  - Handle Telegram 4096 char limit (split if needed)
  - Preserve links integrity

#### 4. Sender
- **Technology:** python-telegram-bot (Bot API)
- **Responsibility:** Deliver digest to authorized user
- **Security:** User ID whitelist verification
- **Features:**
  - Split long messages automatically
  - Error handling and retry logic
  - Silent mode (ignore unauthorized users)

#### 5. Scheduler
- **Technology:** APScheduler
- **Responsibility:** Daily execution at 8 AM UTC
- **Features:**
  - Persistent scheduling (survives restart)
  - Job execution logging
  - Error notifications

#### 6. Bot Commands
- **Technology:** python-telegram-bot
- **Commands:**
  - `/digest` - Generate digest for last 24 hours instantly
  - `/status` - Show bot status and next scheduled run
  - `/help` - Command list (optional)
- **Security:** Only respond to authorized user ID

---

## Technology Stack

### Core Dependencies

```python
# requirements.txt
telethon>=1.34.0          # Telegram User API
python-telegram-bot>=20.0 # Bot API (async version)
openai>=1.0.0             # OpenAI API client
APScheduler>=3.10.0       # Task scheduling
python-dotenv>=1.0.0      # Environment variables
PyYAML>=6.0               # Configuration files
aiohttp>=3.9.0            # Async HTTP client
```

### System Requirements
- **Python:** 3.10+
- **OS:** Linux (Ubuntu 22.04 LTS recommended)
- **RAM:** 512 MB minimum, 1 GB recommended
- **Disk:** 1 GB (for logs and session files)
- **Network:** Stable internet connection

---

## Configuration

### Directory Structure

```
telebrief/
├── main.py                 # Application entry point
├── config.yaml            # Channel list and settings
├── .env                   # API credentials (gitignored)
├── .env.example           # Template for credentials
├── requirements.txt       # Python dependencies
├── README.md              # Setup and usage guide
├── SPECIFICATION.md       # This document
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── core.py            # generate_digest() function
│   ├── collector.py       # Message collection (Telethon)
│   ├── summarizer.py      # AI summarization (OpenAI)
│   ├── formatter.py       # Markdown generation
│   ├── sender.py          # Bot delivery
│   ├── scheduler.py       # APScheduler setup
│   ├── bot_commands.py    # Bot command handlers
│   ├── config_loader.py   # Config management
│   └── utils.py           # Logging, helpers
├── logs/
│   └── telebrief.log      # Application logs
└── sessions/
    └── user.session       # Telegram session (gitignored)
```

### config.yaml

```yaml
# Telegram channels/chats to monitor
channels:
  - id: "@channelname"
    name: "Display Name"
  - id: -100123456789      # Private chat ID
    name: "Private Group"
  # Add up to 20 channels

# Application settings
settings:
  # Scheduling
  schedule_time: "08:00"   # UTC time for daily digest
  timezone: "UTC"
  lookback_hours: 24       # Message collection window

  # OpenAI
  openai_model: "gpt-4-turbo-preview"
  openai_temperature: 0.7
  max_tokens_per_summary: 500

  # Output
  output_language: "russian"
  use_emojis: true
  include_statistics: true

  # Telegram Bot
  target_user_id: 123456789  # Your Telegram user ID

  # Safety limits
  max_messages_per_channel: 500
  api_timeout: 30
```

### .env

```bash
# Telegram User API (from https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here

# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# OpenAI API Key (from https://platform.openai.com)
OPENAI_API_KEY=sk-proj-...

# Logging
LOG_LEVEL=INFO
```

---

## Data Flow

### Daily Scheduled Flow

```
08:00 UTC - Scheduler triggers
    ↓
[1] Collector.fetch_messages(hours=24)
    - Connect to Telegram (Telethon)
    - For each channel in config:
        * Fetch messages from last 24h
        * Extract: text, sender, timestamp, link
    - Return: List[Message] (all channels combined)
    ↓
[2] Summarizer.summarize_per_channel()
    - Group messages by channel
    - For each channel:
        * Build prompt in Russian
        * Call OpenAI API (gpt-4-turbo)
        * Extract summary (3-5 bullet points)
    - Return: Dict[channel_name: summary]
    ↓
[3] Summarizer.generate_overview()
    - Combine all per-channel summaries
    - Build overview prompt in Russian
    - Call OpenAI API (gpt-4-turbo)
    - Extract: executive summary + insights
    - Return: overview text
    ↓
[4] Formatter.create_digest()
    - Build Markdown structure
    - Add emojis and formatting
    - Include message links
    - Add statistics footer
    - Return: formatted_digest (string)
    ↓
[5] Sender.send_to_user()
    - Connect via Bot API
    - Verify user ID == target_user_id
    - Split if > 4096 chars
    - Send message(s)
    - Log success/failure
    ↓
Complete - Log execution time and stats
```

### Manual Digest Flow (/digest command)

```
User sends: /digest
    ↓
Bot receives update
    ↓
Verify user_id == target_user_id
    ↓
Send: "⏳ Генерирую дайджест..."
    ↓
Call generate_digest(hours=24)
    [Same flow as scheduled, steps 1-4]
    ↓
Send: formatted_digest
    ↓
Send: "✅ Дайджест готов!"
```

---

## Prompt Engineering

### System Prompt (Russian Output)

```python
SYSTEM_PROMPT = """
Ты - профессиональный ассистент по созданию новостных дайджестов.

КРИТИЧЕСКИ ВАЖНО: Всегда отвечай ТОЛЬКО на русском языке, независимо от языка входных сообщений.

Ты получишь сообщения на разных языках (английский, русский, украинский, китайский, и т.д.).
Твоя задача: проанализировать контент и предоставить качественное резюме на русском языке.

Сохраняй контекст, нюансы и важные детали при переводе и суммаризации.
"""
```

### Per-Channel Summary Prompt

```python
PER_CHANNEL_TEMPLATE = """
Проанализируй следующие сообщения из Telegram-канала "{channel_name}" и создай краткое резюме на русском языке.

Сфокусируйся на:
- 📰 Важных новостях и анонсах
- 💬 Ключевых обсуждениях и дебатах
- ✅ Принятых решениях или выводах
- 🔗 Полезных ресурсах и ссылках

Формат ответа:
- 3-5 информативных пунктов (bullet points)
- Каждый пункт: 1-2 предложения
- Используй эмодзи для категоризации
- Будь лаконичен но информативен

Сообщения (всего: {message_count}):
---
{messages}
---

Ответь ТОЛЬКО на русском языке.
"""
```

### Combined Overview Prompt

```python
OVERVIEW_TEMPLATE = """
Создай общий ежедневный дайджест на русском языке на основе следующих резюме по каналам.

Резюме по каналам:
---
{channel_summaries}
---

Структура ответа:

1. **Краткий обзор** (2-3 предложения):
   - Выдели главные темы дня
   - Укажи пересекающиеся темы между каналами
   - Выдели наиболее важные события

2. **Детали по каналам**:
   - Для каждого канала сохрани его резюме
   - Добавь контекст если тема упоминается в нескольких каналах
   - Используй соответствующие эмодзи

Тон: профессиональный, информативный, вовлекающий
Язык: ТОЛЬКО русский

Ответь ТОЛЬКО на русском языке.
"""
```

---

## Cost Analysis

### Daily Cost Breakdown (GPT-4-turbo)

**Assumptions:**
- 20 channels
- 100 messages per channel per day = 2,000 total messages
- Average message: 100 tokens
- Per-channel summaries: 20 channels × 200 tokens = 4,000 tokens
- Combined overview: 1,000 tokens

**Token Usage:**
```
Input tokens:
- Messages: 2,000 × 100 = 200,000 tokens
- Per-channel prompts: 20 × 200 = 4,000 tokens
- Overview prompt: 1,000 tokens
Total input: ~205,000 tokens

Output tokens:
- Per-channel summaries: 20 × 200 = 4,000 tokens
- Combined overview: 500 tokens
Total output: ~4,500 tokens
```

**Pricing (GPT-4-turbo-preview):**
- Input: $0.01 per 1K tokens
- Output: $0.03 per 1K tokens

**Daily Cost:**
```
Input: 205K × $0.01 / 1K = $2.05
Output: 4.5K × $0.03 / 1K = $0.14
Total per day: $2.19
```

**Monthly Cost:**
```
$2.19 × 30 days = $65.70 per month
```

**With instant digests:** Add ~$2-3 per manual /digest call

**Annual Cost:** ~$788 per year

---

## Security & Privacy

### Credential Management

1. **Environment Variables:**
   - All secrets in `.env` file
   - File permissions: `chmod 600 .env`
   - Never commit to git (`.gitignore`)

2. **Telegram Session:**
   - Session file: `sessions/user.session`
   - Contains authentication state
   - Must be backed up securely
   - Add to `.gitignore`

3. **API Key Security:**
   - OpenAI: Rotate keys every 90 days
   - Telegram: Bot token from @BotFather (revocable)
   - User API: From my.telegram.org (2FA recommended)

### Access Control

1. **Bot Commands:**
   ```python
   AUTHORIZED_USER_ID = config.target_user_id

   def is_authorized(user_id: int) -> bool:
       return user_id == AUTHORIZED_USER_ID
   ```
   - Only authorized user can trigger commands
   - Other users ignored silently (no error message)

2. **Message Collection:**
   - Uses user's Telegram account
   - Can access private channels user is member of
   - Respects Telegram privacy settings

3. **Data Retention:**
   - Messages processed in-memory only
   - No persistent storage of message content
   - Logs contain only metadata (no message text)

### VPS Security

1. **SSH Access:**
   - Key-based authentication only
   - Disable password login
   - Change default SSH port

2. **Firewall:**
   ```bash
   ufw allow ssh
   ufw enable
   ```

3. **Updates:**
   ```bash
   apt update && apt upgrade -y
   ```
   - Run weekly

4. **Process Isolation:**
   - Run as non-root user
   - Use systemd service with limited permissions

---

## Error Handling

### Error Scenarios & Responses

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| **OpenAI API failure** | Retry 3× with exponential backoff | Delayed digest (max 5 min) |
| **OpenAI rate limit** | Wait and retry | Delayed digest |
| **Telegram rate limit** | Exponential backoff | Delayed digest |
| **Channel unavailable** | Skip channel, log warning | Partial digest sent |
| **Bot can't send** | Log error, retry once | No digest (error logged) |
| **Invalid config** | Fail at startup | App won't start |
| **Network timeout** | Retry with increased timeout | Delayed digest |

### Logging Strategy

```python
# Log Levels
INFO:    Normal operations (digest sent, commands executed)
WARNING: Recoverable errors (channel skipped, retry needed)
ERROR:   Failed operations (digest not sent, API errors)
DEBUG:   Detailed execution flow (development only)
```

**Log Format:**
```
2025-12-14 08:00:15 [INFO] Scheduled digest job started
2025-12-14 08:00:16 [INFO] Collecting messages from 20 channels
2025-12-14 08:01:23 [INFO] Collected 1,847 messages
2025-12-14 08:01:25 [WARNING] Channel @oldchannel unavailable, skipping
2025-12-14 08:02:34 [INFO] Generated per-channel summaries
2025-12-14 08:02:58 [INFO] Generated combined overview
2025-12-14 08:03:01 [INFO] Digest sent successfully to user 123456789
2025-12-14 08:03:01 [INFO] Execution time: 2m 46s | Cost: $2.19
```

**Log Rotation:**
```python
# logs/telebrief.log
# Rotate daily, keep 30 days
# Max size: 100 MB per file
```

---

## Implementation Plan

### Phase 1: Core MVP (Priority 1)

**Goal:** Working digest generation and delivery

**Tasks:**
1. ✅ Project structure setup
2. ✅ Configuration loading (YAML + .env)
3. ✅ Message collector (Telethon integration)
4. ✅ Summarizer (OpenAI integration with Russian prompts)
5. ✅ Formatter (Markdown generation)
6. ✅ Sender (Bot API delivery)
7. ✅ Core function: `generate_digest(hours=24)`
8. ✅ Logging setup

**Deliverable:** Manual execution via `python main.py` generates and sends digest

**Estimate:** 2-3 days

---

### Phase 2: Automation (Priority 1)

**Goal:** Scheduled and on-demand execution

**Tasks:**
1. ✅ APScheduler integration (8 AM UTC daily)
2. ✅ Bot command handler setup
3. ✅ `/digest` command implementation
4. ✅ `/status` command implementation
5. ✅ User authorization check
6. ✅ Error handling and retry logic

**Deliverable:** Fully automated system with bot commands

**Estimate:** 1-2 days

---

### Phase 3: Deployment (Priority 1)

**Goal:** Production-ready VPS deployment

**Tasks:**
1. ✅ VPS setup and security hardening
2. ✅ Python environment configuration
3. ✅ Systemd service creation
4. ✅ First-time authentication (phone verification)
5. ✅ Log rotation setup
6. ✅ Backup strategy (session file)
7. ✅ Monitoring setup
8. ✅ Documentation (README, setup guide)

**Deliverable:** Production system running 24/7

**Estimate:** 1 day

---

### Phase 4: Testing & Optimization (Priority 2)

**Goal:** Stable and optimized operation

**Tasks:**
1. ✅ Test with high-volume channels
2. ✅ Optimize token usage
3. ✅ Fine-tune prompts for Russian output quality
4. ✅ Handle edge cases (empty channels, rate limits)
5. ✅ Cost monitoring and reporting
6. ✅ Performance profiling

**Deliverable:** Optimized, stable system

**Estimate:** 2-3 days

---

### Total Timeline: 6-9 days of focused development

---

## Setup Instructions

### Prerequisites

1. **Telegram App Credentials:**
   - Visit: https://my.telegram.org
   - Login with your phone number
   - Go to "API Development Tools"
   - Create new application
   - Copy `api_id` and `api_hash`

2. **Telegram Bot:**
   - Open Telegram, search @BotFather
   - Send `/newbot`
   - Follow prompts, choose name and username
   - Copy bot token
   - Send `/setprivacy` → choose your bot → Disable
     (Required for bot to work in groups)

3. **OpenAI API Key:**
   - Visit: https://platform.openai.com
   - Create account / login
   - Go to API keys section
   - Create new key
   - Copy key (starts with `sk-`)

4. **Your Telegram User ID:**
   - Open Telegram, search @userinfobot
   - Send any message
   - Copy your user ID (number)

### Installation Steps

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# 3. Clone repository (or create project)
cd ~
mkdir telebrief && cd telebrief
# (If using git: git clone <repo-url> && cd telebrief)

# 4. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 6. Configure credentials
cp .env.example .env
nano .env
# Fill in your credentials, then save (Ctrl+X, Y, Enter)

# 7. Configure channels
nano config.yaml
# Add your channels, then save

# 8. First run (will prompt for phone verification)
python main.py
# Enter your phone number when prompted
# Enter verification code from Telegram
# App will generate and send first digest

# 9. Set up as systemd service (runs on startup)
sudo nano /etc/systemd/system/telebrief.service

# Paste:
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

# Save and exit, then:
sudo systemctl daemon-reload
sudo systemctl enable telebrief
sudo systemctl start telebrief

# 10. Check status
sudo systemctl status telebrief

# View logs
tail -f logs/telebrief.log
```

---

## Usage

### Daily Operation

**Automatic:**
- Digest generated and delivered daily at 8 AM UTC
- No manual intervention required

**Manual Digest:**
1. Open Telegram
2. Find your bot (the one you created with @BotFather)
3. Send: `/digest`
4. Wait 1-2 minutes
5. Receive digest

**Check Status:**
1. Send: `/status`
2. See next scheduled time, configured channels, etc.

### Managing Channels

**Add/Remove Channels:**
```bash
# SSH to your VPS
cd ~/telebrief
nano config.yaml
# Edit channels list, save

# Restart service
sudo systemctl restart telebrief
```

### Monitoring

**Check Logs:**
```bash
# Real-time
tail -f ~/telebrief/logs/telebrief.log

# Last 100 lines
tail -n 100 ~/telebrief/logs/telebrief.log

# Search for errors
grep ERROR ~/telebrief/logs/telebrief.log
```

**Check Service Status:**
```bash
sudo systemctl status telebrief
```

**Restart if Needed:**
```bash
sudo systemctl restart telebrief
```

---

## Maintenance

### Regular Tasks

**Weekly:**
- Check logs for errors: `grep ERROR logs/telebrief.log`
- Verify digests are being delivered
- Check disk space: `df -h`

**Monthly:**
- Review OpenAI API costs: https://platform.openai.com/usage
- Update config if channels changed
- System updates: `sudo apt update && sudo apt upgrade -y`

**Quarterly:**
- Rotate OpenAI API key
- Review and optimize prompts if needed
- Backup session file: `cp sessions/user.session sessions/backup/`

### Troubleshooting

**Digest not received:**
```bash
# Check service running
sudo systemctl status telebrief

# Check logs
tail -n 100 logs/telebrief.log

# Restart
sudo systemctl restart telebrief
```

**Bot not responding to commands:**
```bash
# Verify bot token in .env
cat .env | grep BOT_TOKEN

# Check logs for bot errors
grep "bot" logs/telebrief.log -i

# Test bot manually
python -c "from telegram import Bot; Bot('YOUR_BOT_TOKEN').get_me()"
```

**Authentication errors:**
```bash
# Session file may be corrupted
rm sessions/user.session

# Restart (will prompt for phone verification again)
sudo systemctl restart telebrief
journalctl -u telebrief -f
# Follow prompts in logs
```

---

## Success Criteria

### MVP Success

- ✅ Digest generated and delivered daily at 8 AM UTC
- ✅ All 20 channels included in digest
- ✅ Messages in any language processed correctly
- ✅ Output always in Russian language
- ✅ `/digest` command works for instant generation
- ✅ `/status` command shows correct information
- ✅ Only authorized user can interact with bot
- ✅ Clickable links to original messages work
- ✅ Markdown formatting renders correctly
- ✅ Runs unattended for 7 days without issues

### Quality Metrics

- **Reliability:** 95%+ successful deliveries (28/30 days)
- **Performance:** < 3 minutes execution time
- **Accuracy:** Summaries capture key points (manual review)
- **Cost:** Within $80/month budget
- **Uptime:** 99%+ (service running)

---

## Future Enhancements (Post-MVP)

**Not part of current scope, but possible future additions:**

1. **Advanced Bot Commands:**
   - `/digest 6h` - Custom time ranges
   - `/channels` - Manage channels via bot
   - `/stats` - Detailed statistics

2. **Cost Optimization:**
   - Smart sampling for high-volume channels
   - Message deduplication
   - Hybrid model approach (GPT-3.5 + GPT-4)

3. **Enhanced Output:**
   - Topic clustering across channels
   - Trending themes detection
   - Weekly/monthly summaries

4. **Digest Archive:**
   - Save digests to files
   - Searchable history
   - Web dashboard

5. **Multi-User Support:**
   - Multiple authorized users
   - Per-user channel preferences
   - Shared digests

6. **Analytics:**
   - Cost tracking dashboard
   - Channel activity statistics
   - Summary quality metrics

---

## Appendix

### A. Example Digest Output

```markdown
# 📊 Ежедневный дайджест - 14 декабря 2025

## 🎯 Краткий обзор

Сегодня основные темы: запуск Python 3.13 с улучшениями производительности
обсуждался в нескольких технических каналах, криптовалютный рынок показал
высокую волатильность на фоне новостей о регулировании, и появились важные
обновления в сфере искусственного интеллекта от крупных компаний.

---

## 💻 TechCrunch

- 🚀 **Python 3.13 релиз**: Официально выпущена новая версия с JIT-компиляцией,
  обещающей до 2x прирост производительности [🔗](https://t.me/techcrunch/12345)
- 🤖 **OpenAI анонсировала GPT-5**: Следующее поколение модели ожидается
  в Q1 2026 с мультимодальными возможностями [🔗](https://t.me/techcrunch/12350)
- 📱 **Apple vs EU**: Новые требования по interoperability для App Store
  вступают в силу в январе [🔗](https://t.me/techcrunch/12358)

## 💰 Crypto News

- 📈 **Bitcoin волатильность**: Цена колебалась между $43K и $46K на фоне
  слухов о одобрении spot ETF [🔗](https://t.me/cryptonews/8923)
- ⚠️ **SEC предупреждение**: Новая схема мошенничества с fake staking pools,
  уже пострадало >$10M [🔗](https://t.me/cryptonews/8930)
- 🔐 **Ethereum upgrade**: Успешно завершен тестнет для Dencun upgrade,
  mainnet ожидается в феврале [🔗](https://t.me/cryptonews/8935)

## 🧑‍💻 Developer Chat

- 💬 **Обсуждение архитектуры**: Активная дискуссия о microservices vs
  monolith для нового проекта, консенсус пока не достигнут [🔗](https://t.me/c/123456/4567)
- 🔗 **Полезный ресурс**: Кто-то поделился отличным гайдом по Kubernetes
  security best practices [🔗](https://t.me/c/123456/4580)
- ✅ **Решение**: Команда выбрала PostgreSQL вместо MongoDB для нового
  сервиса аналитики [🔗](https://t.me/c/123456/4592)

---

📈 **Статистика**: 20 каналов, 1,847 сообщений обработано
⏱️ Дайджест за: 13 декабря 08:00 - 14 декабря 08:00 UTC
```

### B. Sample config.yaml

```yaml
channels:
  - id: "@techcrunch"
    name: "TechCrunch"
  - id: "@thenextweb"
    name: "The Next Web"
  - id: "@verge"
    name: "The Verge"
  - id: "@hackernews"
    name: "Hacker News"
  - id: "@reddit_programming"
    name: "r/Programming"
  - id: "@cryptonews"
    name: "Crypto News"
  - id: "@bitcoin"
    name: "Bitcoin"
  - id: "@ethereum"
    name: "Ethereum"
  - id: -1001234567890
    name: "Private Dev Chat"
  - id: -1009876543210
    name: "Startup Founders"
  # Add more channels up to ~20

settings:
  schedule_time: "08:00"
  timezone: "UTC"
  lookback_hours: 24
  openai_model: "gpt-4-turbo-preview"
  openai_temperature: 0.7
  max_tokens_per_summary: 500
  output_language: "russian"
  use_emojis: true
  include_statistics: true
  target_user_id: 123456789
  max_messages_per_channel: 500
  api_timeout: 30
```

### C. .gitignore

```gitignore
# Environment variables
.env

# Telegram session
sessions/*.session
sessions/*.session-journal

# Logs
logs/*.log

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
.venv/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Backups
*.bak
backup/
```

---

## Document Control

**Version History:**

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-14 | Initial specification | Claude + User |

**Approval:**

- [ ] User reviewed and approved
- [ ] Ready for implementation

---

**END OF SPECIFICATION**
