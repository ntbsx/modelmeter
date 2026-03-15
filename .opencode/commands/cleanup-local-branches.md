---
description: Clean local branches and keep only ones with open PRs
---
You are cleaning local git branches for this repository.

Mode is `$1`.
- If `$1` is empty, treat it as `dry-run`.
- Supported modes: `dry-run`, `apply`, `force`.
- If mode is invalid, print usage and stop: `/cleanup-local-branches [dry-run|apply|force]`.

Goal:
- Keep local branches that have an open PR.
- Delete local branches that do not have an open PR.

Safety rules:
- Never delete: `main`, `master`, `develop`, or the current checked-out branch.
- Never delete a protected branch, even in `force` mode.
- If GitHub CLI is missing or not authenticated, stop with actionable instructions.

Execution steps:
1. Verify tools:
   - `git --version`
   - `gh --version`
   - `gh auth status`
2. Sync refs:
   - `git fetch --prune`
3. Determine current branch and local branches:
   - current: `git rev-parse --abbrev-ref HEAD`
   - local branches: `git for-each-ref --format='%(refname:short)' refs/heads`
4. For each local branch that is not protected, check if it has an open PR:
   - `gh pr list --head <branch> --state open --json number --jq 'length'`
   - If result > 0, keep it.
   - If result == 0, mark it as deletion candidate.
5. Print plan before any deletion:
   - Mode
   - Protected branches
   - Branches kept (with open PR)
   - Deletion candidates (no open PR)
6. Apply behavior:
   - `dry-run`: do not delete; print what would be removed.
   - `apply`: try `git branch -d <branch>` for each candidate.
   - `force`: try `git branch -d <branch>` first, then `git branch -D <branch>` only if safe delete fails.
7. Print final summary:
   - Kept count/list
   - Deleted count/list
   - Failed deletions count/list with reason

Output style:
- Be concise.
- Show clear sections: `Plan`, `Actions`, `Summary`.
- Include exact commands run for delete actions.
