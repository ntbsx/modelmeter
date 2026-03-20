---
description: Prepare and publish a stable or release-candidate GitHub release
---

You are creating a release in this git repository.

Arguments:
- Mode is `$1`.
- Release type is `$2`.

Supported values:
- Mode: `dry-run`, `apply` (default: `dry-run`)
- Type: `stable`, `rc` (default: `stable`)

Usage:
- `/create_release`
- `/create_release dry-run`
- `/create_release dry-run stable`
- `/create_release dry-run rc`
- `/create_release apply stable`
- `/create_release apply rc`

If mode or type is invalid, print usage and stop:
`/create_release [dry-run|apply] [stable|rc]`

Policy:
- Stable releases are allowed only on branch `main`.
- RC releases are allowed on any branch, including `main`.

Safety rules:
- Require a clean working tree before making changes.
- Stop immediately on failed commands.
- Never overwrite an existing tag.
- Always create annotated tags.

Execution steps:

## Phase 1: Preconditions

1. Verify tools:
   - `git --version`
   - `gh --version`
   - `gh auth status`

2. Read branch and state:
   - `git rev-parse --abbrev-ref HEAD`
   - `git status --porcelain`
   - Fail if working tree is not clean.

3. Enforce branch policy:
   - If type is `stable` and branch is not `main`, fail with:
     `✗ Stable releases must run from main. Use /create_release apply rc on this branch or switch to main.`

## Phase 2: Version and Tag Resolution

4. Read canonical backend version from `pyproject.toml`.

5. Resolve release target:
   - For `stable`:
     - Run `make version-stamp` (bumps monthly patch and syncs `web/package.json`).
     - Read stamped version from `pyproject.toml` as `RELEASE_VERSION`.
     - Set `RELEASE_TAG=v${RELEASE_VERSION}`.
   - For `rc`:
     - Read base version from `pyproject.toml` as `BASE_VERSION` (must be `YYYY.M.x`).
     - Find existing tags matching `v${BASE_VERSION}rcN`.
     - Compute next `N` (`1` when none exists).
     - Set `RELEASE_VERSION=${BASE_VERSION}rc${N}`.
     - Set `RELEASE_TAG=v${RELEASE_VERSION}`.

6. Tag guard:
   - Check `git rev-parse -q --verify "refs/tags/${RELEASE_TAG}"`.
   - If tag exists, fail.

## Phase 3: Changelog Update

7. Ensure `CHANGELOG.md` contains `## [Unreleased]`.

8. Promote unreleased section:
   - Replace the first `## [Unreleased]` heading with `## [${RELEASE_VERSION}] - <YYYY-MM-DD>`.
   - Insert a fresh empty unreleased section directly above it:

```markdown
## [Unreleased]

## [${RELEASE_VERSION}] - <YYYY-MM-DD>
```

9. Keep existing release note body as-is unless empty.

## Phase 4: Verification

10. Run full release checks:
    - `make release-check`

## Phase 5: Commit, Tag, and Push

11. Stage release metadata:
    - `git add CHANGELOG.md pyproject.toml web/package.json`

12. Commit message:
    - Stable: `release: bump to ${RELEASE_VERSION}`
    - RC: `release: cut ${RELEASE_VERSION}`

13. Create annotated tag:
    - `git tag -a "${RELEASE_TAG}" -m "Release ${RELEASE_TAG}"`

14. Push:
    - `git push origin <current-branch>`
    - `git push origin "${RELEASE_TAG}"`

15. Output summary:
    - Branch
    - Release type
    - Version
    - Tag
    - Commit SHA
    - Next step: monitor `.github/workflows/release.yml`

Dry-run behavior:

- In `dry-run`, do not modify files and do not run write operations.
- Print:
  - branch policy result
  - computed next version/tag
  - exact commands that would run in order
  - files expected to change (`CHANGELOG.md`, `pyproject.toml`, `web/package.json` for stable; `CHANGELOG.md` for rc)

Error handling:

- If repo is dirty: `✗ Working tree is not clean`
- If tag exists: `✗ Tag already exists: <tag>`
- If changelog heading missing: `✗ CHANGELOG.md is missing ## [Unreleased]`
- If `make release-check` fails: print failing command and stop.

Output style:

- Be concise and step-oriented.
- Use symbols: `✓` success, `✗` failure, `⚠` warning.
