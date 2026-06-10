# Security Policy

## Supported Versions

Telebrief is under active development. Only the latest release on `main` receives security fixes.

| Version | Supported |
| ------- | --------- |
| latest `main` | ✅ |
| older commits | ❌ |

## Reporting a Vulnerability

Please **do not** report security vulnerabilities through public GitHub issues.

Instead, use [GitHub private vulnerability reporting](https://github.com/belaytzev/Telebrief/security/advisories/new): go to the repository's **Security** tab → **Report a vulnerability**.

Include as much of the following as you can:

- Description of the vulnerability and its impact
- Steps to reproduce or a proof of concept
- Affected component (e.g., `src/collector.py`, Docker image, bot commands)
- Suggested fix, if you have one

You can expect an initial response within a few days. Please allow time for a fix before any public disclosure.

## Scope Notes

Telebrief handles sensitive credentials. Areas of particular interest:

- Telegram API credentials and session files (`sessions/`)
- AI provider API keys (OpenAI, Anthropic) loaded from `.env` / `config.yaml`
- Data stored in SQLite/PostgreSQL backends
- The Docker deployment path (`Dockerfile`, `docker-compose.yml`)

If you find credentials or session data being logged, leaked into digests, or exposed via bot commands, that is a vulnerability — please report it.
