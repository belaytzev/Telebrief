# Security policy

## Supported versions

Telebrief is still under active development, and only the latest release on `main` gets security fixes.

| Version | Supported |
| ------- | --------- |
| latest `main` | ✅ |
| older commits | ❌ |

## Reporting a vulnerability

Please **don't** report vulnerabilities in public GitHub issues.

Use [GitHub private vulnerability reporting](https://github.com/belaytzev/Telebrief/security/advisories/new) instead: open the repository's **Security** tab and click **Report a vulnerability**.

It helps if you include:

- what the vulnerability is and what an attacker could do with it
- steps to reproduce, or a proof of concept
- the affected component, for example `src/collector.py`, the Docker image or bot commands
- a suggested fix, if you have one

Expect a first reply within a few days. Please give us time to fix the issue before you disclose it publicly.

## What to look at

Telebrief handles sensitive credentials, so these areas matter most:

- Telegram API credentials and session files (`sessions/`)
- AI provider API keys (OpenAI, Anthropic) loaded from `.env` or `config.yaml`
- Data stored in the SQLite or PostgreSQL backend
- The Docker deployment (`Dockerfile`, `docker-compose.yml`)

Credentials or session data showing up in logs, in digests or in bot command replies count as a vulnerability. Please report them.
