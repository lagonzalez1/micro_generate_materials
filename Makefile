# Makefile at project root

PYTHON := python3
PYTEST := pytest

TEST_DIR := Models/test
TEST_AMAZON_MODEL := $(TEST_DIR)/test_amazon_model.py
TEST_GEMINI_MODEL := $(TEST_DIR)/test_gemini_model.py

.PHONY: help test lint clean venv

help:
	@echo "Available targets:"
	@echo "  make test     - run unit tests with pytest"
	@echo "  make lint     - run flake8 lint checks"
	@echo "  make clean    - remove Python cache/__pycache__ files"
	@echo "  make venv     - create virtual environment"

# Run tests (will install pytest if missing)
test:
	@echo "Running tests in $(TEST_FILE)"
	@$(PYTHON) -m pip install -q pytest
	@$(PYTHON) -m $(PYTEST) $(TEST_AMAZON_MODEL) -v
	@$(PYTHON) -m $(PYTEST) $(TEST_GEMINI_MODEL) -v

# Run lint checks (optional)
lint:
	@$(PYTHON) -m pip install -q flake8
	@$(PYTHON) -m flake8 .

# Clean cache
clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete

# Create virtual environment (default .venv folder)
venv:
	@$(PYTHON) -m venv .venv
	@echo "Virtual environment created in .venv/"