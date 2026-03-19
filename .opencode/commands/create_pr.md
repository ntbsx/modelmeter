---
description: Create a GitHub pull request following the project template
---

You are creating a GitHub pull request for this repository.

Mode is `$1`.
- If `$1` is empty or `dry-run`, show generated PR without executing.
- If `$1` is `apply`, create the PR on GitHub.
- If mode is invalid, print usage: `/create_pr [dry-run|apply]`

## Execution Steps

### Phase 1: Analyze Changes

1. Run commands:
   - `git status --short` - list changed files
   - `git diff --stat` - summary of changes
   - `git log --oneline -10` - recent commit style
   - `git diff --name-only main..HEAD` - files changed vs main

2. Check for uncommitted changes:
   ```bash
   git status --porcelain
   ```
   If any uncommitted changes exist, print error and stop:
   ```
   ✗ You have uncommitted changes. Commit them first with /commit_and_push apply
   ```

3. Check if there are commits to create PR for:
   ```bash
   git log main..HEAD --oneline
   ```
   If empty, print error and stop.

### Phase 2: Read PR Template

4. Read `.github/pull_request_template.md` to get the template format.

### Phase 3: Auto-detect PR Type

5. Determine type from changed files:
   - `.github/workflows/*.yml` → type: `ci`
   - `tests/**`, `**/*.test.*` → type: `test`
   - `*.md`, `docs/**` → type: `docs`
   - `pyproject.toml`, `uv.lock`, `web/package.json` → type: `chore`
   - `src/modelmeter/**` → type: `feat` or `fix`
   - `web/src/**` → type: `feat` or `fix` or `refactor`
   - Default → type: `refactor`

6. Inspect diff for keywords to refine type:
   - "bug", "fix", "issue", "error" → type: `fix`
   - "breaking", "migration" → type: `feat` with BREAKING CHANGE

7. Determine scope from file paths (e.g., `web`, `backend`, `api`, `ci`)

8. Generate title following conventional commits:
   ```
   <type>(<scope>): <imperative-verb-first-description>
   ```
   Subject: 50-72 characters.

### Phase 4: Fill Template

9. Fill out each section of the template:

**Summary**: What changed and why. Use 1-2 sentences.

**Version Impact**:
- Check if `pyproject.toml` or `web/package.json` changed
- Mark appropriate checkbox
- If version changed, note the new version

**API Contract Impact**:
- Check for changes to API routes, schemas, or endpoints
- Look for files matching: `**/api/**`, `**/routes/**`, `**/schemas/**`
- Mark appropriate checkbox

**OpenAPI/Generated Types**:
- If API contract changed, check if `web/openapi.json`, `web/src/generated/api.ts`, or `web/src/generated/openapi.sha256` were updated
- Mark appropriate checkbox

**Verification**:
- Run these commands and capture results:
  ```bash
  npm run --prefix web build 2>&1
  npm run --prefix web test -- --run 2>&1
  npm run --prefix web lint 2>&1
  ```
- Mark `make release-check` if applicable
- List any additional checks run

**Test Scope**:
- Describe what was tested
- Note any known gaps or follow-ups

**Release/Rollout Notes**:
- Note any migration steps, env changes, or operational notes
- If none, can leave empty or say "None"

### Phase 5: Handle Existing PR

10. Check if PR already exists:
    ```bash
    gh pr list --head $(git branch --show-current) --json number,title,state
    ```

11. If PR exists:
    - Print warning: "PR #N already exists for this branch"
    - Ask if user wants to close and recreate, or update existing

### Phase 6: Create PR

12. Generate PR body by filling template with gathered info

13. Format with checkboxes properly formatted for GitHub markdown:
    - `[x]` for checked
    - `[ ]` for unchecked

## Phase 7: Dry-Run Mode (default)

14. If mode is `dry-run` or empty:
    - Print "=== DRY RUN ==="
    - Print "Title:" followed by the title
    - Print "Base:" (main)
    - Print "Body:" followed by the filled template
    - Print "Would run: gh pr create --title '...' --body '...'"
    - Stop here. Do NOT create PR.

## Phase 8: Apply Mode

15. If mode is `apply`:

16. If existing PR found, close it first:
    ```bash
    gh pr close <number>
    ```

17. Create PR:
    ```bash
    gh pr create \
      --title "<title>" \
      --body "<filled template>" \
      --base main
    ```

18. Print summary:
    ```
    ✓ PR created: <URL>
    ✓ Title: <title>
    ✓ Base: main ← compare:main
    ```

## Error Handling

- If uncommitted changes: Print error and stop
- If no commits: Print error and stop
- If `gh pr create` fails: Print error with details
- If `gh` not authenticated: Print "Authenticate with: gh auth login"

## Output Style

- Be concise
- Use clear symbols: ✓ success, ✗ failure, ⚠ warning
- Show verification command results inline
- In dry-run, show complete PR without executing
