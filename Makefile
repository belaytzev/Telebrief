# Makefile for Telebrief

.PHONY: help install install-dev test lint format clean run

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make test         - Run tests with coverage"
	@echo "  make test-fast    - Run tests without coverage"
	@echo "  make lint         - Run all linters"
	@echo "  make format       - Format code with black and isort"
	@echo "  make clean        - Remove build artifacts"
	@echo "  make run          - Run the application"
	@echo "  make pre-commit   - Install pre-commit hooks"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

test:
	pytest --cov=src --cov-report=html --cov-report=term-missing -v

test-fast:
	pytest -v

test-unit:
	pytest -v -m unit

test-integration:
	pytest -v -m integration

lint:
	@echo "Running Black..."
	black --check src tests
	@echo "\nRunning isort..."
	isort --check-only src tests
	@echo "\nRunning Flake8..."
	flake8 src tests
	@echo "\nRunning MyPy..."
	mypy src
	@echo "\nRunning Pylint..."
	pylint src tests --fail-under=8.0
	@echo "\nRunning Vulture (unused code detection)..."
	vulture src vulture_whitelist.py --min-confidence 80

format:
	black src tests
	isort src tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name coverage.xml -delete
	find . -type f -name .coverage -delete
	rm -rf dist build *.egg-info

run:
	python main.py

pre-commit:
	pre-commit install
	@echo "Pre-commit hooks installed!"

check: lint test
	@echo "All checks passed!"
