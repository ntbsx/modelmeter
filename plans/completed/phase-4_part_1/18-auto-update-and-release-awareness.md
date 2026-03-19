# Feature Plan: Auto-Update and Release Awareness

## Objective
Add a safe update workflow so users can discover and apply newer ModelMeter releases directly from CLI, while preserving explicit user control.

## Why This Matters
- Users currently rely on manual release discovery.
- Faster upgrades reduce time-to-fix and accelerate feature adoption.
- Existing release assets and installer logic already support deterministic installs.

## Scope

### In Scope
- Update metadata fetch from GitHub release API.
- CalVer-aware version comparison.
- Explicit update commands:
  - `modelmeter update check`
  - `modelmeter update apply`
- Optional passive update notifications with local rate-limit cache.
- Config/env toggles for update behavior.

### Out of Scope
- Forced background updates.
- Auto-restart behavior after update.
- Changes to distribution channel strategy.

## Workstreams

### Workstream A: Updater Core and Version Semantics (Priority 1)

#### Deliverables
- Add updater service for latest release resolution.
- CalVer-safe compare logic aligned with canonical version policy.
- Failure-tolerant network and parse behavior.

#### Acceptance Criteria
- Correctly identifies newer/equal/older versions.
- Network failures return actionable, non-destructive errors.

#### Validation
- Unit tests for version comparison and API failure cases.

---

### Workstream B: CLI Update Commands (Priority 2)

#### Deliverables
- Add `modelmeter update check` output with installed/latest details.
- Add `modelmeter update apply` with:
  - optional target version
  - method selection (`auto|pipx|pip`)
  - dry-run mode
- Reuse release asset preference (wheel first, archive fallback).

#### Acceptance Criteria
- Check command is read-only.
- Apply command behavior is explicit and predictable.

#### Validation
- CLI integration tests with mocked release metadata/install calls.

---

### Workstream C: Passive Release Awareness (Priority 3)

#### Deliverables
- Add optional update-available hints in selected commands.
- Add local cache file for check cadence control.
- Add opt-out controls via env/config.

#### Acceptance Criteria
- Hints do not block or degrade primary command output.
- Opt-out behavior is honored consistently.

#### Validation
- Tests for hint cadence, cache invalidation, and opt-out.

---

### Workstream D: Docs and Release Runbook Alignment (Priority 4)

#### Deliverables
- Update README usage examples for check/apply flows.
- Update release runbook with updater compatibility requirements.
- Add troubleshooting notes (pipx/pip/path/network constraints).

#### Acceptance Criteria
- Docs reflect implemented command behavior accurately.
- Release process remains aligned with updater expectations.

#### Validation
- Manual doc-follow verification in a clean shell.

## Milestones

### Milestone 1: Update Intelligence Ready
- Workstream A complete.

### Milestone 2: User-Initiated Update Flow
- Workstream B complete.

### Milestone 3: Awareness and Ops Completeness
- Workstream C and D complete.

## Definition of Done
- Users can check and apply updates directly from CLI.
- Update checks are safe, explicit, and non-forced.
- Docs and release process are aligned with updater behavior.

## Completion Checklist
- [ ] Workstream A complete
- [ ] Workstream B complete
- [ ] Workstream C complete
- [ ] Workstream D complete
