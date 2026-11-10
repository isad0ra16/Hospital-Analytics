.PHONY: hooks hooks-uninstall help install install-notebook test lint format check fetch-data verify convert validate processed audit indicators analysis pipeline

help:  ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

install:  ## Create .venv with the exact locked dependencies (runtime + dev)
	uv sync --locked

install-notebook:  ## Also install Jupyter
	uv sync --locked --group notebook

test:  ## Run the test suite
	uv run pytest

lint:  ## Static checks (no changes)
	uv run ruff check .
	uv run ruff format --check .

format:  ## Auto-format code
	uv run ruff format .
	uv run ruff check --fix .

check: lint test  ## Everything that must pass before a commit

convert:  ## Untreated .dbc -> Parquet conversion (source must be registered in data/MANIFEST.json)
	uv run hospital-analytics convert

validate:  ## Validate the raw Parquet against historical references and the manifest
	uv run hospital-analytics validate

fetch-data:  ## Recover the original .dbc from the GitHub Release and verify it against the manifest
	./scripts/fetch_source.sh

verify:  ## Check every file listed in data/MANIFEST.json (exists + SHA-256)
	uv run hospital-analytics verify

processed:  ## Build the processed layer (original fields + derived columns)
	uv run hospital-analytics build-processed

audit:  ## Read-only data audit -> reports/audit/
	uv run hospital-analytics audit

indicators:  ## Historical indicators, pandas x DuckDB -> reports/indicators/
	uv run hospital-analytics indicators

analysis:  ## Descriptive exploratory analyses -> reports/analysis/
	uv run hospital-analytics analysis

pipeline: convert validate processed audit indicators analysis  ## Everything after fetch-data

hooks:  ## Enable the versioned git hooks (scripts/git-hooks) for this clone - explicit opt-in
	git config core.hooksPath scripts/git-hooks
	@echo "git hooks enabled: core.hooksPath=scripts/git-hooks (undo with: make hooks-uninstall)"

hooks-uninstall:  ## Disable the versioned git hooks for this clone
	git config --unset core.hooksPath || true
	@echo "git hooks disabled"
