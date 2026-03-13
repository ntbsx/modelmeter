.PHONY: dev backend frontend setup test format lint typecheck

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
	uv run pyright

test:
	uv run pytest
