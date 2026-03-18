---
description: Analyze changes, generate commit message, run pre-commit/pre-push hooks, and push to origin
---

You are committing and pushing changes to this git repository.

Mode is `$1`.
- If `$1` is empty or `dry-run`, show generated commit message and what would happen without making changes.
- If `$1` is `apply`, execute all steps: run hooks, stage, commit, and push.
- If mode is invalid, print usage and stop: `/commit_and_push [dry-run|apply]`.

Goal:
- Auto-detect commit type from most-affected files changed.
- Generate a standardized commit message following conventional commits format.
- Run pre-commit hooks (with auto-fix retry).
- Run pre-push hooks on main/develop branches (with auto-fix retry).
- Push to origin.

Safety rules:
- Never skip pre-commit hooks.
- Never skip pre-push hooks when on main or develop branch.
- Skip pre-push hooks on feature branches (CI will catch issues).
- If auto-fix modifies files during pre-commit, re-run hooks until clean before committing.
- If unfixable issues remain, abort and show errors.

Execution steps:

## Phase 1: Analyze Changes

1. Run git commands to gather context:
   - `git status --short` to get list of changed files
   - `git diff --stat` to get summary of changes
   - `git diff` to get full diff content
   - `git log --oneline -10` to get recent commit style

2. Determine changed files and categorize:
   - `.github/workflows/*.yml` → type: `ci`
   - `tests/**`, `**/*.test.*` → type: `test`
   - `*.md`, `docs/**` → type: `docs`
   - `pyproject.toml`, `uv.lock`, `web/package.json`, `package-lock.json` → type: `chore`
   - `scripts/**` → type: `chore`
   - `src/modelmeter/**`, `web/src/**` → type: `feat` or `fix` (inspect diff for keywords)
   - `.opencode/commands/**` → type: `chore`
   - Default → type: `refactor`

3. Determine scope (most-affected area):
   - Analyze file paths to find primary area (e.g., `ci`, `web`, `api`, `scripts`, `config`, `*`)

4. Auto-detect type:
   - If only one category of files changed, use that type.
   - If multiple categories, use type of most-affected area.
   - Inspect diff for keywords: "bug", "fix", "issue", "error" → type: `fix`
   - Inspect diff for "breaking", "migration" → type: `feat` with BREAKING CHANGE note

## Phase 2: Generate Commit Message

5. Generate commit message:
   - Subject: `<type>(<scope>): <imperative-verb-first-description>`
   - Subject should be 50-72 characters.
   - If subject exceeds 72 characters, show warning in dry-run mode.
   - Description: 1-2 sentences explaining WHY (not what).
   - Bullets: 3-7 key changes, each starting with a verb in past tense or present tense.

6. Format the message:
   ```
   <type>(<scope>): <subject>

   <description sentence 1>.
   <description sentence 2>.

   - <bullet 1>
   - <bullet 2>
   - <bullet 3>
   ```

## Phase 3: Dry-Run Mode (default)

7. If mode is `dry-run` or empty:
   - Print "=== DRY RUN ==="
   - Print "Generated commit message:"
   - Print the full message
   - If subject > 72 chars, print "⚠ Warning: Subject line exceeds 72 characters"
   - Print "Staged files: " followed by list
   - Print "Would run:"
     - `✓ pre-commit run --all-files`
     - `✓ git add .`
     - `✓ git commit -m "..."`
     - If on main/develop: `✓ pre-commit run --hook-stage pre-push --all-files`
     - If on feature branch: `⊘ pre-push hooks skipped (feature branch)`
     - `✓ git push origin <branch>`
   - Stop here. Do NOT make any changes.

## Phase 4: Apply Mode

8. If mode is `apply`:

9. Run pre-commit hooks:
   - `uv run pre-commit run --all-files`
   - If auto-fixable issues found, re-run until clean (max 3 iterations).
   - If unfixable issues remain, abort with error message.
   - If files were auto-fixed, re-stage them with `git add -A`.

10. Stage all changes:
    - `git add -A`

11. Create commit:
    - `git commit -m "<generated message>"`
    - Capture commit SHA: `git rev-parse HEAD`

12. Detect current branch:
    - `git rev-parse --abbrev-ref HEAD`

13. If branch is `main` or `develop`:
    - Run pre-push hooks: `uv run pre-commit run --hook-stage pre-push --all-files`
    - If auto-fixable issues found, re-run until clean (max 3 iterations).
    - If unfixable issues remain, abort with error. DO NOT push.

14. Push to origin:
    - `git push origin <branch>`
    - Capture push result.

15. Print summary:
    ```
    ✓ Commit: <sha> "<subject>"
    ✓ Pushed to origin/<branch>
    ✓ Pre-commit hooks: passed
    ✓ Pre-push hooks: <passed|skipped (feature branch)>
    ```

## Error Handling

- If pre-commit fails with unfixable issues:
  - Print "✗ Pre-commit hooks failed"
  - List failing hooks and their errors
  - Print "Fix the issues above and run /commit_and_push again"
  - Do NOT commit or push.

- If pre-push fails with unfixable issues:
  - Print "✗ Pre-push hooks failed"
  - List failing hooks and their errors
  - Print "Commit was created but NOT pushed. Fix issues and run /commit_and_push again"
  - Do NOT push.

- If git commit fails:
  - Print "✗ Git commit failed" with error message.
  - Do NOT push.

- If git push fails:
  - Print "✗ Git push failed" with error message.
  - Print "Commit was created. Push manually or fix issues."

## Output Style

- Be concise.
- Use clear symbols: ✓ success, ✗ failure, ⚠ warning, ⊘ skipped
- Show exact commands for errors.
- In dry-run, show a clear plan before any action.
- In apply mode, show progress as steps complete.
