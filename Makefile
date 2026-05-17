.PHONY: setup install uninstall build test doctor clean docker help

SHELL := /bin/bash
REPO_ROOT := $(shell pwd)
VENV := $(REPO_ROOT)/.venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip
SOCKET_DIR := ${XDG_RUNTIME_DIR}/whisper
WAIT_TIMEOUT := 30

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## First-time setup: create venv, install deps, copy .env, create socket dir, build Docker
	@echo "=== First-time setup ==="
	@echo ""
	@echo "Checking prerequisites..."
	@command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
	@python_version=$$(python3 --version | awk '{print $$2}'); \
	installed_major=$$(echo $$python_version | cut -d. -f1); \
	installed_minor=$$(echo $$python_version | cut -d. -f2); \
	if [ "$$installed_major" -lt 3 ] || ([ "$$installed_major" -eq 3 ] && [ "$$installed_minor" -lt 11 ]); then \
		echo "ERROR: python3 >= 3.11 required (found $$python_version)"; exit 1; \
	fi; \
	echo "  ✓ python3 $$python_version"
	@command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }
	@echo "  ✓ docker"
	@command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker compose not found"; exit 1; }
	@echo "  ✓ docker compose"
	@command -v xdotool >/dev/null 2>&1 || { echo "WARNING: xdotool not found (required for dictation)"; }
	@echo "  ✓ xdotool"
	@echo ""
	@echo "Creating virtual environment at $(VENV)..."
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv "$(VENV)"; \
		echo "  ✓ venv created"; \
	else \
		echo "  ✓ venv already exists"; \
	fi
	@echo ""
	@echo "Installing package with dev dependencies..."
	@$(PIP) install -e ".[dev]"
	@echo "  ✓ package installed"
	@echo ""
	@echo "Setting up .env file..."
	@if [ ! -f ".env" ]; then \
		cp .env.example .env; \
		echo "  ✓ .env created from .env.example"; \
	else \
		echo "  ✓ .env already exists"; \
	fi
	@echo ""
	@echo "Creating socket directory at $(SOCKET_DIR)..."
	@mkdir -p "$(SOCKET_DIR)" || { echo "ERROR: Failed to create $(SOCKET_DIR)"; exit 1; }
	@chmod 700 "$(SOCKET_DIR)"
	@echo "  ✓ socket directory created"
	@echo ""
	@echo "Building and starting Docker container..."
	@docker compose up -d --build
	@echo "  ✓ Docker container started"
	@echo ""
	@echo "Waiting for inference server socket (timeout: $(WAIT_TIMEOUT)s)..."
	@timeout=$(WAIT_TIMEOUT); elapsed=0; \
	while [ $$elapsed -lt $$timeout ]; do \
		if [ -S "$(SOCKET_DIR)/whisper.sock" ]; then \
			echo "  ✓ socket found"; \
			break; \
		fi; \
		sleep 1; \
		elapsed=$$((elapsed + 1)); \
	done; \
	if [ $$elapsed -eq $$timeout ]; then \
		echo "  ✗ socket not found after $$timeout seconds"; \
		echo ""; \
		echo "Running diagnostics..."; \
		$(PYTHON) -m whisper_hotkey.cli doctor || true; \
		echo ""; \
		echo "Setup completed with warnings. Check the output above."; \
		exit 1; \
	fi
	@echo ""
	@echo "Running diagnostics..."
	@$(PYTHON) -m whisper_hotkey.cli doctor
	@echo ""
	@echo "=== Setup complete ==="
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run: easy-local-whisper-hotkey run"
	@echo "  2. Press Ctrl+Space to record"

install: ## pipx install . (system-wide CLI)
	@echo "Installing system-wide CLI..."
	pipx install .

uninstall: ## pipx uninstall easy-local-whisper-hotkey
	@echo "Uninstalling system-wide CLI..."
	pipx uninstall easy-local-whisper-hotkey || true

build: ## python3 -m build (create wheel)
	@echo "Building package..."
	python3 -m build

test: ## Run unit tests
	@echo "Running tests..."
	$(PYTHON) -m unittest discover -s tests -t . -p 'test_*.py' -v

doctor: ## easy-local-whisper-hotkey doctor
	@echo "Running diagnostics..."
	easy-local-whisper-hotkey doctor

clean: ## Remove build artifacts, __pycache__, .egg-info
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	@echo "Cleaning Python cache..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "  ✓ clean complete"

docker: ## docker compose up -d --build
	@echo "Building and starting Docker container..."
	docker compose up -d --build
	@echo "  ✓ Docker container started"