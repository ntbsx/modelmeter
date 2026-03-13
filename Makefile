.PHONY: dev backend frontend setup test format lint typecheck gen-types version-stamp version-sync version-check contract-policy-check release-check package-build package-clean perf-check

# Run both backend and frontend concurrently
dev:
	@echo "Starting ModelMeter Dev Servers..."
	@make -j 2 backend frontend

# Start the FastAPI backend
backend:
	@echo "Starting backend API on port 8000..."
	uv run uvicorn modelmeter.api.app:app --reload --port 8000

# Start the Vite React frontend
frontend:
	@echo "Starting frontend dev server..."
	npm run --prefix web dev

# Helper command to install all dependencies
setup:
	uv sync
	npm install --prefix web

# Helper commands for quality checks
format:
	uv run ruff format

lint:
	uv run ruff check

typecheck:
	uv run python -m pyright

test:
	uv run python -m pytest

gen-types:
	npm run --prefix web gen:types

version-stamp:
	uv run python scripts/stamp_calver.py
	make version-sync

version-sync:
	uv run python scripts/sync_product_version.py

version-check:
	uv run python scripts/sync_product_version.py --check

contract-policy-check:
	uv run python scripts/check_contract_version_policy.py

release-check:
	uv run ruff format --check
	make lint
	make version-check
	make contract-policy-check
	npm run --prefix web lint
	npm run --prefix web check:types
	make typecheck
	make test

package-build:
	npm run --prefix web build
	uv run python scripts/prepare_web_dist.py
	uv build

package-clean:
	rm -rf src/modelmeter/web_dist dist

perf-check:
	uv run python scripts/perf_baseline.py
