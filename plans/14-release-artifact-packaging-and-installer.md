# Feature Plan: Release Artifact Packaging and Installer

## Objective
Package ModelMeter so installed artifacts include the web app, and provide a public bash installer that installs from GitHub Release assets.

## Why This Matters
- Current install paths are Python-package oriented, but release-distribution flow is not finalized for GitHub artifacts.
- Users should be able to install and run `modelmeter serve` without cloning the repo or building frontend assets locally.
- A stable public installer improves onboarding and release adoption.

## Scope

### In Scope
- Bundle built frontend (`web/dist`) into Python wheel/sdist.
- Serve packaged frontend assets at runtime in installed environments.
- Add tag-driven GitHub release pipeline that publishes wheel/sdist artifacts.
- Add public bash installer at `scripts/install.sh` supporting latest and pinned versions.
- Document install flow in `README.md`.

### Out of Scope
- Private-token installer flow (repo is public).
- PyPI publishing pipeline changes.
- Multi-arch native binary packaging.

## Workstreams

### Workstream A: Package Bundled Frontend Assets (Priority 1)

#### Deliverables
- Build frontend during release packaging workflow.
- Include bundled assets in package data under module path (e.g. `modelmeter/web_dist/**`).
- Ensure wheel/sdist contain `index.html` and static assets.

#### Acceptance Criteria
- Built wheel includes web assets.
- Installed package can locate frontend assets from package resources.

#### Validation
- Build wheel/sdist locally and inspect contents.
- Install wheel in clean environment and verify files exist.

---

### Workstream B: Runtime Static Serving from Package (Priority 2)

#### Deliverables
- Update app static resolution to prefer packaged assets.
- Keep local `web/dist` fallback for dev mode.
- Return clear response if no static assets are available.

#### Acceptance Criteria
- `modelmeter serve` serves UI from installed artifact.
- Existing local dev serving behavior continues to work.

#### Validation
- Run server from installed wheel and verify `/` + static asset paths.
- Run server from repo checkout and verify fallback behavior.

---

### Workstream C: GitHub Release Artifact Pipeline (Priority 3)

#### Deliverables
- Add release jobs in `.github/workflows/release.yml` (tag-only):
  - build artifacts (web + wheel/sdist)
  - publish artifacts to GitHub Release assets
- Keep non-release CI flow unchanged for branch/MR pipelines.

#### Acceptance Criteria
- Tag `vX.Y.Z` produces downloadable release artifacts.
- Artifacts are consistently named and discoverable.

#### Validation
- Create test tag and confirm release asset availability.

---

### Workstream D: Public Bash Installer (Priority 4)

#### Deliverables
- Add `scripts/install.sh` with:
  - latest-release install (default)
  - pinned version via `--version X.Y.Z`
  - `pipx` preferred install path
  - `python -m pip --user` fallback
  - post-install sanity check (`modelmeter info`)

#### Acceptance Criteria
- Installer works on public GitHub release assets without auth.
- Latest and pinned installs both succeed.

#### Validation
- Test installer on clean Linux/macOS shells.
- Test both default and `--version` flows.

---

### Workstream E: Documentation and Operational Verification (Priority 5)

#### Deliverables
- Update `README.md` with installer usage examples.
- Add troubleshooting notes (PATH, pipx missing, Python version).
- Add release smoke step to verify install from produced artifact.

#### Acceptance Criteria
- Docs are sufficient for first-time users to install and run web UI.
- Release flow includes an explicit install smoke test.

#### Validation
- Follow README from clean environment and complete install successfully.

## Milestones

### Milestone 1: Artifact Completeness
- Workstream A complete.

### Milestone 2: Installed Runtime Parity
- Workstream B complete.

### Milestone 3: Distribution Automation
- Workstream C and D complete.

### Milestone 4: Adoption Readiness
- Workstream E complete.

## Definition of Done
- Release wheel/sdist include bundled web assets.
- `modelmeter serve` works directly from installed release artifact.
- Public `scripts/install.sh` supports latest and pinned versions.
- GitHub tag releases publish installable assets consistently.
- README reflects the final install workflow.

## Completion Checklist
- [x] Workstream A complete
- [x] Workstream B complete
- [x] Workstream C complete
- [x] Workstream D complete
- [x] Workstream E complete
