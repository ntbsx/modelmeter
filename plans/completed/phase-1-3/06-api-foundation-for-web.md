# Feature Plan: API Foundation for Web (DONE)

## Objective
Expose analytics via HTTP without duplicating business logic.

## Scope
- FastAPI service wrapping core analytics
- Endpoint parity with CLI data commands
- OpenAPI schema generation
- CORS/config suitable for local web app development
- FastAPI app scaffolded with uv-managed dependencies and typed response models

## Deliverables
- Endpoints:
  - `GET /summary`
  - `GET /daily`
  - `GET /models`
  - `GET /models/{model}`
  - `GET /projects`
  - `GET /live/snapshot`
  - `GET /health` and `GET /doctor`
- Shared response models imported from core
- API error model and status mapping

## Key Decisions
- Keep auth optional for localhost phase
- Use query params mirroring CLI flags
- Single source of truth: core services

## Acceptance Criteria
- API responses match CLI `--json` contracts
- OpenAPI docs usable for frontend integration
- Basic load/polling behavior verified locally
