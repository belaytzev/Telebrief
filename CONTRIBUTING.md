# Contributing to Telebrief

Thanks for your interest in Telebrief. Bug reports, features, documentation fixes and questions are all welcome.

## Ways to contribute

- Report a bug: open a [bug report](https://github.com/belaytzev/Telebrief/issues/new?template=bug_report.yml).
- Suggest a feature: open a [feature request](https://github.com/belaytzev/Telebrief/issues/new?template=feature_request.yml).
- Improve the documentation. Typo fixes and clarifications make a good first contribution.
- Send code: bug fixes, new filters, AI providers or storage backends (see [Extensibility](README.md#extensibility)).
- Add a translation. UI strings are in `src/ui_strings.py`, and a new language doesn't touch anything else.

## Development setup

Telebrief needs **Python 3.14+** and uses [uv](https://docs.astral.sh/uv/) to manage the environment.

```bash
# Clone your fork
git clone https://github.com/<your-username>/Telebrief.git
cd Telebrief

# Create a virtual environment with the locked dependencies
uv sync --frozen --extra dev

# Install pre-commit hooks
uv run pre-commit install

# Copy and fill in configuration
cp config.yaml.example config.yaml
cp .env.example .env
```

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`; the Docker image and CI install exactly the locked versions. To add or bump a dependency, run `uv add <package>` (or `uv lock --upgrade-package <package>`) and commit both files.

> **macOS:** the `markdownlint` pre-commit hook needs Ruby 3.1 or newer, and macOS ships 2.6. Skip the hook locally and let CI run it:
>
> ```bash
> SKIP=markdownlint uv run pre-commit run --all-files
> ```

## Tests and checks

CI runs the same checks, so run them all before you push:

```bash
# Tests (coverage threshold must stay above the configured minimum)
uv run pytest tests/ -v

# Type checking
uv run mypy src/

# Linting
uv tool run ruff check src/ tests/
uv run flake8 src/ tests/

# Formatting (CI pins black 24.10.0 — always run before pushing)
uv run black src/ tests/
```

The Makefile has shortcuts for these: `make test`, `make lint`, `make format`, `make check`.

### Testing conventions

- Fixtures are in `tests/conftest.py` (`sample_config`, `mock_logger`).
- Async tests use `@pytest.mark.asyncio`.
- New code comes with tests, and a bug fix comes with a regression test.

## Code style

- Formatting: black 24.10.0, the version pinned in `.pre-commit-config.yaml`.
- Import order: isort.
- Linting: flake8 with `max-complexity=10`.
- Types: mypy. New code should be fully typed.
- black turns Protocol method stubs into one-liners, which flake8 rejects, so suppress the warning on each such line:

  ```python
  class MyProtocol(Protocol):
      async def save(self, items: list) -> int: ...  # noqa: E704
  ```

- Markdown files in `docs/` need a blank line before and after every fenced code block (markdownlint MD031).

## Commit messages

The project uses [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat(grouper): deterministic QUALITY GATE filter
fix(collector): handle empty channel history
docs: clarify per-channel lookback configuration
```

The usual types are `feat`, `fix`, `docs`, `refactor`, `test` and `chore`.

## Pull requests

1. Fork the repository and branch off `main`.
2. Make your changes. Keep each PR about one thing.
3. Run all the checks locally: tests, mypy, ruff, black and flake8.
4. Open a PR against `main` and describe what you changed and why.
5. CI has to pass before review. A maintainer then reviews and merges.

For bigger changes, such as a new module or a change in architecture, please open an issue first so we can agree on the approach before you write the code.

## Reporting bugs

Please include:

- Telebrief version or commit hash
- Python version and OS
- AI provider (OpenAI, Ollama or Anthropic)
- The relevant `config.yaml` settings, with **API keys, phone numbers and session data removed**
- Steps to reproduce, what you expected and what happened
- Log output, if you have it (the `logs/` directory)

**Never post Telegram session files, API credentials or the contents of `.env` in an issue.**

## Questions

Ask in a [discussion or an issue](https://github.com/belaytzev/Telebrief/issues).

## Code of conduct

By taking part in this project you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
