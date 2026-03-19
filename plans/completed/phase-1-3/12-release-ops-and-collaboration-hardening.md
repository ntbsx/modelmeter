# Feature Plan: Release Ops and Collaboration Hardening

## Objective
Strengthen release and team workflows so changes ship reliably with clear auditability and lower coordination overhead.

## Why This Matters
- Product features are now broad enough that process gaps can cause regressions.
- Release checks exist, but contributor workflow consistency is still mostly manual.
- Better templates and automation reduce ambiguity for versioning, contracts, and QA.

## Scope

### In Scope
- Changelog process and release notes structure
- Merge request template with quality/versioning prompts
- CI feedback improvements and staged quality gates
- Version-bump policy enforcement for API contract drift
- Contributor workflow docs for day-to-day development and release prep

### Out of Scope
- Hosted deployment infrastructure changes
- Secret management redesign
- New runtime features unrelated to release/process reliability

## Workstreams

### Workstream A: Changelog and Release Notes (Priority 1)

#### Deliverables
- Add `CHANGELOG.md` using Keep a Changelog style.
- Define release note sections:
  - Added
  - Changed
  - Fixed
  - Breaking
  - Docs/Tooling
- Document how and when entries are added (per MR vs pre-release squash).

#### Acceptance Criteria
- Every version bump has a corresponding changelog entry.
- Release notes are generated from a predictable structure.

#### Validation
- Manual spot check on latest release flow.

---

### Workstream B: Merge Request Template (Priority 2)

#### Deliverables
- Add `.github/pull_request_template.md` with required checklist:
  - version impact (patch/minor/major)
  - API contract changed? if yes, what changed
  - `make release-check` run result
  - OpenAPI/types regeneration confirmation
  - test scope summary

#### Acceptance Criteria
- New MRs include explicit versioning and contract impact statements.
- Reviewers can quickly validate release risk.

#### Validation
- Open a test MR and confirm template autoload and usability.

---

### Workstream C: CI Quality Gate Refinement (Priority 3)

#### Deliverables
- Split/organize CI jobs for faster signal:
  - quick checks first (format/lint/version/type)
  - slower checks after (tests/build)
- Ensure frontend lint is explicitly executed in CI.
- Add clearer failure messages where possible.

#### Acceptance Criteria
- CI gives actionable failures earlier in the pipeline.
- Frontend lint regressions fail CI deterministically.

#### Validation
- Run sample branches with intentional failures and verify stage behavior.

---

### Workstream D: Contract and Version Policy Enforcement (Priority 4)

#### Deliverables
- Add script/check that detects OpenAPI snapshot changes and requires documented version impact.
- Ensure policy alignment:
  - backward-compatible contract change => minor bump minimum
  - breaking contract change => major bump
- Keep existing `make version-check` as required gate.

#### Acceptance Criteria
- Contract changes cannot merge silently without version intent.
- Policy is documented and enforced by automation.

#### Validation
- Simulate additive and breaking contract edits and verify expected gate behavior.

---

### Workstream E: Contributor and Release Runbook (Priority 5)

#### Deliverables
- Add concise runbook in docs for:
  - feature branch quality loop
  - release prep sequence
  - rollback guidance for bad release artifacts
- Include exact commands for consistency.

#### Acceptance Criteria
- A contributor can run the release flow without tribal knowledge.
- Recovery path is documented for common release mistakes.

#### Validation
- Dry run by another contributor (or self-check from clean clone).

## Milestones

### Milestone 1: Collaboration Baseline
- Workstream A and B complete.

### Milestone 2: CI Signal and Enforcement
- Workstream C and D complete.

### Milestone 3: Operational Readiness
- Workstream E complete and verified.

## Definition of Done
- Release and MR workflows are documented and enforced.
- CI catches versioning, contract, and frontend quality regressions consistently.
- Changelog process is active and used for the next release.

## Completion Checklist
- [x] Workstream A complete
- [x] Workstream B complete
- [x] Workstream C complete
- [x] Workstream D complete
- [x] Workstream E complete
