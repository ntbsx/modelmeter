# Contributing to ModelMeter

Thank you for your interest in contributing to ModelMeter! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/ntbsx/modelmeter.git
cd modelmeter

# Install all dependencies (Python + Node)
make setup

# Run backend + frontend dev servers
make dev
```

The web UI will be available at `http://localhost:5173` and the API at `http://127.0.0.1:8000`.

## Project Structure

```
modelmeter/
├── src/modelmeter/     # Python backend + CLI
│   ├── api/            # FastAPI routes
│   ├── cli/            # Typer CLI commands
│   ├── core/           # Business logic
│   └── data/           # Data persistence
├── web/                # React frontend
│   ├── src/
│   │   ├── components/ # Reusable UI components
│   │   ├── pages/      # Route-level views
│   │   ├── lib/        # API helpers and utilities
│   │   └── generated/  # Auto-generated OpenAPI types
├── tests/              # Python tests (pytest)
└── scripts/            # Build and release scripts
```

## Development Workflow

### Running Quality Checks

Before submitting a PR, run:

```bash
make format      # Format code with Ruff
make lint        # Lint with Ruff
make typecheck   # Type check with Pyright (strict)
make test        # Run all pytest tests
```

For frontend:

```bash
npm run --prefix web lint
npm run --prefix web test
```

### Running a Single Test

```bash
# Single file
uv run pytest tests/test_api.py

# Single test function
uv run pytest tests/test_api.py::test_health_endpoint

# By keyword
uv run pytest -k "health and not auth"
```

### Regenerating API Types

If you change the FastAPI API schema:

```bash
make gen-types
```

This updates `web/openapi.json` and `web/src/generated/api.ts`.

## Versioning

ModelMeter uses a single CalVer product version (`YYYY.M.x`) across backend, CLI, and frontend.

- **Source of truth:** `pyproject.toml` (`[project].version`)
- **Frontend version:** `web/package.json` (must match backend)

Common commands:

```bash
make version-sync   # Sync frontend version to backend
make version-check  # Verify versions are aligned
```

## Pull Request Guidelines

1. **Create a branch** from `main` with a descriptive name (e.g., `fix/login-error`, `feat/new-chart`).

2. **Keep changes focused.** One PR should address one concern.

3. **Run all checks** before submitting:
   ```bash
   make release-check
   ```

4. **Write clear commit messages.** Focus on the "why" rather than the "what".

5. **Update tests** if you change behavior. Add tests for new features.

6. **Update documentation** if you change developer workflows or user-facing behavior.

## Code Style

### Python

- Ruff is the source of truth for formatting and linting
- Pyright strict mode is enabled; maintain complete type hints
- Prefer absolute imports from `modelmeter.*`
- Max line length: 100 characters

### TypeScript/React

- TypeScript strict mode; avoid `any`
- Use generated OpenAPI types from `web/src/generated/api.ts`
- Components use PascalCase naming

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- See the [README](README.md) for detailed usage instructions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
