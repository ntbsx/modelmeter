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


def _resolve_base_ref(arg_base_ref: str | None) -> str:
    if arg_base_ref:
        return arg_base_ref

    mr_target = os.getenv("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "").strip()
    if mr_target:
        return f"origin/{mr_target}"

    default_branch = os.getenv("CI_DEFAULT_BRANCH", "").strip()
    if default_branch:
        return f"origin/{default_branch}"

    return "HEAD~1"


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
    base_ref = _resolve_base_ref(args.base_ref)

    changed_output = _run_git(["diff", "--name-only", f"{base_ref}...HEAD"], cwd=root)
    changed_files = {line.strip() for line in changed_output.splitlines() if line.strip()}

    if "web/openapi.json" not in changed_files:
        print("Contract check: no OpenAPI contract changes detected.")
        return 0

    violations: list[str] = []

    if "pyproject.toml" not in changed_files:
        violations.append(
            "OpenAPI contract changed but pyproject.toml version was not updated.",
        )

    required_generated = {
        "web/src/generated/api.ts",
        "web/src/generated/openapi.sha256",
    }
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
