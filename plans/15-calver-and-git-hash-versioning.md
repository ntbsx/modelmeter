# Feature Plan: CalVer + Git Hash Versioning

## Objective
Migrate ModelMeter versioning from SemVer to a CalVer-based canonical version, while exposing a runtime/display version that includes the latest short git hash.

## Target Version Model
- Canonical release version (source of truth): `YYYY.M.D`
  - Examples: `2026.3.13`, `2026.3.14`
  - Stored in `pyproject.toml` and synchronized to `web/package.json`
- Runtime/display version: `YYYY.M.D+<shortsha>`
  - Example: `2026.3.13+c210fbd`
  - Used for CLI/info/doctor and other user-facing runtime metadata

## Why This Matters
- CalVer communicates release timing directly.
- Adding short hash improves traceability to exact build/source state.
- Keeping OpenAPI version stable (without hash) avoids snapshot churn every commit.

## Scope

### In Scope
- Canonical version policy update to CalVer
- Runtime git hash suffix for display version
- Tooling updates for version sync/check/stamp
- Tests and docs updates

### Out of Scope
- API path namespacing changes (`/api/v1`)
- Distribution channel changes (PyPI/GitLab release flow)
- Breaking API contract redesign

## Workstreams

### Workstream A: Version Utility Refactor (Priority 1)

#### Deliverables
- Extend `src/modelmeter/common/version.py` with clear separation:
  - `get_base_version()` -> canonical CalVer
  - `get_git_short_sha()` -> short hash when available
  - `get_product_version()` -> runtime/display version with hash suffix
- Safe fallbacks for environments without `.git` metadata.

#### Acceptance Criteria
- Base version always resolves deterministically.
- Runtime version includes hash when available and falls back gracefully when unavailable.

#### Validation
- Unit/versioning tests with and without git context.

---

### Workstream B: OpenAPI Stability and Runtime Display (Priority 2)

#### Deliverables
- Keep FastAPI/OpenAPI `info.version` on base CalVer only.
- Use full `+hash` runtime version for CLI info/doctor output.

#### Acceptance Criteria
- OpenAPI snapshot no longer changes per commit solely due to hash changes.
- CLI outputs include traceable build suffix where available.

#### Validation
- `tests/test_openapi_contract.py` remains stable.
- CLI smoke checks show expected version format.

---

### Workstream C: Version Sync and CalVer Enforcement (Priority 3)

#### Deliverables
- Update `scripts/sync_product_version.py` to enforce CalVer format for canonical version.
- Keep backend/frontend version sync behavior unchanged in principle.
- Add helpful failure messages for invalid canonical version format.

#### Acceptance Criteria
- `make version-check` fails when canonical version is not valid CalVer.
- Backend and frontend canonical versions remain aligned.

#### Validation
- Positive and negative test cases for sync/check script.

---

### Workstream D: Version Stamp Automation (Priority 4)

#### Deliverables
- Add script (e.g. `scripts/stamp_calver.py`) to set canonical version from date.
- Add Make target (`make version-stamp`) to update version and sync frontend.

#### Acceptance Criteria
- One command updates canonical version consistently.
- Result passes `make version-check`.

#### Validation
- Local run of stamp + sync + checks.

---

### Workstream E: Tests and Documentation (Priority 5)

#### Deliverables
- Update `tests/test_versioning.py` for new model:
  - canonical version checks against pyproject/package.json
  - runtime display version includes hash when available
- Update docs (`README.md`, `AGENTS.md`) for CalVer + hash policy.

#### Acceptance Criteria
- Tests assert intended version behavior clearly.
- Docs match implemented behavior and release flow.

#### Validation
- `make release-check` passes.
- Manual `modelmeter info` output sanity check.

## Milestones

### Milestone 1: Version Core Ready
- Workstream A complete.

### Milestone 2: Stable Contracts + Display Traceability
- Workstream B complete.

### Milestone 3: Tooling and Automation
- Workstream C and D complete.

### Milestone 4: Verification and Adoption
- Workstream E complete.

## Definition of Done
- Canonical versioning uses CalVer in backend/frontend manifests.
- Runtime display version includes short git hash when available.
- OpenAPI snapshot remains stable across commits unless API contract actually changes.
- Version tooling and docs are updated and validated.

## Completion Checklist
- [x] Workstream A complete
- [x] Workstream B complete
- [x] Workstream C complete
- [x] Workstream D complete
- [x] Workstream E complete
