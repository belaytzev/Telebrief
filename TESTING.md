# Testing Guide for Telebrief

This document provides comprehensive information about testing, linting, and code quality for Telebrief.

---

## Quick Start

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
make test

# Run linters
make lint

# Format code
make format
```

---

## Test Suite

### Running Tests

**All tests with coverage:**
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
# Or simply:
make test
```

**Fast tests (no coverage):**
```bash
pytest -v
# Or:
make test-fast
```

**Unit tests only:**
```bash
pytest -m unit
# Or:
make test-unit
```

**Integration tests only:**
```bash
pytest -m integration
# Or:
make test-integration
```

**Specific test file:**
```bash
pytest tests/test_config_loader.py -v
```

**Specific test function:**
```bash
pytest tests/test_utils.py::test_format_timerange -v
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_config_loader.py    # Config loading tests
├── test_utils.py            # Utility function tests
├── test_formatter.py        # Digest formatting tests
├── test_summarizer.py       # AI summarization tests
├── test_sender.py           # Bot sending tests
└── test_core.py             # Core function tests
```

### Test Markers

Tests are marked with the following markers:

- `@pytest.mark.unit` - Fast unit tests (mocked dependencies)
- `@pytest.mark.integration` - Integration tests (may require credentials)
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_credentials` - Tests requiring API credentials

**Run specific markers:**
```bash
pytest -m unit -v
pytest -m "not slow" -v
```

### Coverage

**View coverage report:**
```bash
# Generate HTML report
pytest --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Coverage requirements:**
- Minimum coverage: 70%
- Target coverage: 80%+
- Critical modules should have 90%+ coverage

---

## Linting and Code Quality

### Available Linters

1. **Black** - Code formatting
2. **isort** - Import sorting
3. **Flake8** - Style guide enforcement
4. **MyPy** - Static type checking
5. **Pylint** - Comprehensive code analysis

### Running Linters

**All linters:**
```bash
make lint
```

**Individual linters:**

```bash
# Black (formatting check)
black --check src tests

# isort (import sorting check)
isort --check-only src tests

# Flake8 (linting)
flake8 src tests

# MyPy (type checking)
mypy src

# Pylint (code quality)
pylint src tests
```

### Auto-formatting

**Format all code:**
```bash
make format
```

This runs:
- `black` - Formats code
- `isort` - Sorts imports

---

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality.

### Installation

```bash
# Install hooks
make pre-commit
# Or:
pre-commit install
```

### Manual Run

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run flake8 --all-files
```

### Hooks Included

- **trailing-whitespace** - Remove trailing whitespace
- **end-of-file-fixer** - Ensure files end with newline
- **check-yaml** - Validate YAML files
- **check-added-large-files** - Prevent large files
- **detect-private-key** - Prevent committing secrets
- **black** - Code formatting
- **isort** - Import sorting
- **flake8** - Linting
- **mypy** - Type checking
- **bandit** - Security checks

### Skipping Hooks

**Skip all hooks (not recommended):**
```bash
git commit --no-verify -m "message"
```

**Skip specific hook:**
```bash
SKIP=mypy git commit -m "message"
```

---

## GitHub Actions CI/CD

### Workflows

The project includes a comprehensive CI/CD pipeline that runs on every push and pull request:

**File:** `.github/workflows/ci.yml`

### CI Jobs

1. **Lint** - Code quality checks
   - Black formatting
   - isort import sorting
   - Flake8 linting
   - MyPy type checking
   - Pylint analysis

2. **Test** - Test suite
   - Runs on Python 3.10, 3.11, 3.12
   - Full test coverage
   - Uploads coverage to Codecov

3. **Security** - Security scanning
   - Bandit security linter
   - Safety dependency checker

4. **Build** - Package building
   - Verifies package builds correctly
   - Uploads build artifacts

### Viewing Results

- GitHub Actions tab in your repository
- Status badges in README.md
- Codecov dashboard for coverage

### Adding Status Badges

Add to README.md:

```markdown
![CI](https://github.com/USERNAME/telebrief/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/USERNAME/telebrief/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/telebrief)
```

---

## Writing Tests

### Test Structure

```python
"""Tests for module_name."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.module_name import ClassToTest


@pytest.mark.unit
def test_function_name(sample_config, mock_logger):
    """Test description."""
    # Arrange
    obj = ClassToTest(sample_config, mock_logger)

    # Act
    result = obj.method()

    # Assert
    assert result == expected
```

### Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `mock_env_vars` - Mock environment variables
- `sample_config` - Sample configuration
- `sample_messages` - Sample Telegram messages
- `mock_logger` - Mock logger
- `temp_config_file` - Temporary config file

**Using fixtures:**
```python
def test_something(sample_config, mock_logger):
    obj = MyClass(sample_config, mock_logger)
    # ...
```

### Mocking

**Mock function:**
```python
from unittest.mock import MagicMock, patch

def test_with_mock():
    with patch('src.module.function') as mock_func:
        mock_func.return_value = "mocked"
        result = call_function()
        assert result == "mocked"
```

**Mock async function:**
```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_async_with_mock():
    with patch('src.module.async_function', new=AsyncMock()):
        result = await call_async_function()
        assert result is not None
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

---

## Code Quality Standards

### Style Guidelines

- **Line length:** 100 characters
- **Import order:** stdlib → third-party → first-party → local
- **Docstrings:** Google style
- **Type hints:** Use where appropriate

### Naming Conventions

- **Functions/methods:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private methods:** `_leading_underscore`

### Docstring Format

```python
def function(param1: str, param2: int) -> bool:
    """
    Short description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is invalid
    """
    pass
```

---

## Continuous Integration

### Local Pre-push Checks

Before pushing code, run:

```bash
make check
```

This runs all linters and tests to ensure CI will pass.

### CI Failure Debugging

**Check logs:**
1. Go to GitHub Actions tab
2. Click failed workflow
3. View logs for failed job

**Reproduce locally:**
```bash
# Run exact CI commands
make lint
make test
```

**Common failures:**

1. **Black formatting**
   ```bash
   make format  # Auto-fix
   ```

2. **Flake8 errors**
   ```bash
   flake8 src tests  # View errors
   # Fix manually
   ```

3. **Test failures**
   ```bash
   pytest -v  # Run with verbose output
   pytest --lf  # Re-run last failed
   ```

4. **MyPy type errors**
   ```bash
   mypy src  # View type errors
   # Add type hints or ignores
   ```

---

## Coverage Goals

| Module | Target Coverage | Current |
|--------|----------------|---------|
| config_loader.py | 90% | - |
| utils.py | 90% | - |
| collector.py | 80% | - |
| summarizer.py | 80% | - |
| formatter.py | 90% | - |
| sender.py | 80% | - |
| core.py | 85% | - |
| scheduler.py | 75% | - |
| bot_commands.py | 75% | - |

---

## Troubleshooting

### Tests Failing Locally

```bash
# Clear cache and rerun
pytest --cache-clear -v

# Reinstall dependencies
pip install -r requirements-dev.txt --upgrade

# Check environment
python --version  # Should be 3.10+
```

### Import Errors

```bash
# Ensure src is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in editable mode
pip install -e .
```

### Slow Tests

```bash
# Run with timeout
pytest --timeout=60

# Skip slow tests
pytest -m "not slow"
```

---

## Best Practices

### ✅ Do

- Write tests for new features
- Mock external dependencies
- Use descriptive test names
- Test edge cases and error handling
- Keep tests fast (<1s per test)
- Use fixtures for common setup
- Run linters before committing

### ❌ Don't

- Commit without running tests
- Skip linter warnings
- Test implementation details
- Use sleep() in tests
- Hardcode credentials
- Commit with failing tests

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [Black documentation](https://black.readthedocs.io/)
- [MyPy documentation](https://mypy.readthedocs.io/)
- [pre-commit documentation](https://pre-commit.com/)

---

**Happy testing! 🧪✅**
