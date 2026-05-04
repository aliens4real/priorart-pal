.PHONY: help setup test lint format api-dev api-test api-lint web-dev web-test web-lint web-build infra-test infra-synth infra-diff clean

UV ?= uv
NPM ?= npm

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── one-shots ────────────────────────────────────────────────────────────────

setup: ## Install all dependencies (api + infra + web + pre-commit)
	cd api && $(UV) sync --all-extras
	cd infra && $(UV) sync
	cd web && $(NPM) ci
	pre-commit install || true

test: api-test infra-test web-test ## Run all test suites

lint: api-lint infra-lint web-lint ## Lint everything

format: ## Auto-format Python (ruff) and JS/TS (prettier via pre-commit)
	cd api && $(UV) run ruff format .
	cd infra && $(UV) run ruff format .
	cd web && $(NPM) run lint -- --fix || true

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +
	find . -type d -name .mypy_cache -prune -exec rm -rf {} +
	rm -rf api/.venv infra/.venv web/dist web/node_modules infra/cdk.out

# ─── api ──────────────────────────────────────────────────────────────────────

api-dev: ## Run FastAPI locally on :8000
	cd api && $(UV) run uvicorn priorart_pal.main:app --reload --port 8000

api-test: ## Run backend pytest
	cd api && $(UV) run pytest -q

api-lint: ## Lint backend (ruff + mypy)
	cd api && $(UV) run ruff check .
	cd api && $(UV) run mypy src

# ─── infra ────────────────────────────────────────────────────────────────────

infra-test: ## Run CDK assertion tests
	cd infra && $(UV) run pytest -q

infra-lint: ## Lint infra Python
	cd infra && $(UV) run ruff check .

infra-synth: ## Synthesize CloudFormation (no AWS calls beyond context lookups)
	cd infra && $(UV) run cdk synth --quiet

infra-diff: ## Diff against deployed state (requires AWS creds)
	cd infra && $(UV) run cdk diff

# ─── web ──────────────────────────────────────────────────────────────────────

web-dev: ## Run Vite dev server on :5173
	cd web && $(NPM) run dev

web-test: ## Run vitest single-pass
	cd web && $(NPM) test -- --run

web-lint: ## Lint frontend
	cd web && $(NPM) run lint

web-build: ## Production build
	cd web && $(NPM) run build
