from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _run_git(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _run_git_optional(args: list[str], *, cwd: Path) -> str | None:
    try:
        return _run_git(args, cwd=cwd)
    except subprocess.CalledProcessError:
        return None


def _resolve_base_refs(arg_base_ref: str | None) -> list[str]:
    refs: list[str] = []
    if arg_base_ref:
        refs.append(arg_base_ref)

    github_base_ref = os.getenv("GITHUB_BASE_REF", "").strip()
    if github_base_ref:
        refs.append(f"origin/{github_base_ref}")

    mr_target = os.getenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "").strip()
    if mr_target:
        refs.append(f"origin/{mr_target}")

    default_branch = os.getenv("CI_DEFAULT_BRANCH", "").strip()
    if default_branch:
        refs.append(f"origin/{default_branch}")

    github_before = os.getenv("GITHUB_EVENT_BEFORE", "").strip()
    if github_before and github_before != "0000000000000000000000000000000000000000":
        refs.append(github_before)

    refs.append("HEAD~1")
    return list(dict.fromkeys(refs))


def _changed_files_from_diff_range(*, root: Path, base_ref: str) -> set[str] | None:
    changed_output = _run_git_optional(["diff", "--name-only", f"{base_ref}...HEAD"], cwd=root)
    if changed_output is None:
        return None
    return {line.strip() for line in changed_output.splitlines() if line.strip()}


def _changed_files_ci(*, root: Path, base_refs: list[str]) -> set[str]:
    for base_ref in base_refs:
        changed_files = _changed_files_from_diff_range(root=root, base_ref=base_ref)
        if changed_files is not None:
            return changed_files

    # Fallback for shallow clones and first-commit checkouts where HEAD~1 may not exist.
    changed_output = _run_git_optional(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], cwd=root
    )
    if changed_output is None:
        return set()
    return {line.strip() for line in changed_output.splitlines() if line.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce version bump policy when OpenAPI contract changes.",
    )
    parser.add_argument(
        "--base-ref",
        help=("Git base ref for diff comparison (default: CI target/default branch, then HEAD~1)"),
    )
    args = parser.parse_args()

    root = _project_root()
    base_refs = _resolve_base_refs(args.base_ref)

    in_ci = os.getenv("CI", "").strip().lower() == "true"
    if in_ci:
        changed_files = _changed_files_ci(root=root, base_refs=base_refs)
    else:
        status_output = _run_git(["status", "--porcelain"], cwd=root)
        changed_files = {
            line[3:].strip()
            for line in status_output.splitlines()
            if len(line) > 3 and line[3:].strip()
        }

    if "web/openapi.json" not in changed_files:
        print("Contract check: no OpenAPI contract changes detected.")
        return 0

    violations: list[str] = []

    if "pyproject.toml" not in changed_files:
        violations.append(
            "OpenAPI contract changed but pyproject.toml version was not updated.",
        )

    required_generated = {"web/src/generated/openapi.sha256"}
    missing_generated = sorted(path for path in required_generated if path not in changed_files)
    if missing_generated:
        violations.append(
            "OpenAPI contract changed but generated artifacts were not updated: "
            + ", ".join(missing_generated),
        )

    if violations:
        print("Contract check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Contract check passed: OpenAPI change is accompanied by version + generated updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
