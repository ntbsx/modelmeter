from __future__ import annotations

import argparse
import datetime as dt
import re
import tomllib
from pathlib import Path

STABLE_VERSION_PATTERN = re.compile(
    r"^(?P<year>\d{4})\.(?P<month>[1-9]|1[0-2])\.(?P<patch>\d+)(?:rc\d+)?$"
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _replace_project_version(pyproject_path: Path, new_version: str) -> tuple[str, str]:
    content = pyproject_path.read_text()
    parsed = tomllib.loads(content)
    project = parsed.get("project", {})
    current = project.get("version")
    if not isinstance(current, str):
        raise RuntimeError("Could not read [project].version from pyproject.toml")

    marker = f'version = "{current}"'
    replacement = f'version = "{new_version}"'
    if marker not in content:
        raise RuntimeError("Unable to locate version line in pyproject.toml")

    pyproject_path.write_text(content.replace(marker, replacement, 1))
    return current, new_version


def _parse_existing_version(value: str) -> tuple[int, int, int]:
    match = STABLE_VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise RuntimeError("Current version must use YYYY.M.x or YYYY.M.xrcN before stamping.")
    year = int(match.group("year"))
    month = int(match.group("month"))
    patch = int(match.group("patch"))
    return year, month, patch


def _next_monthly_patch(
    *, current_version: str, target_date: dt.date, patch_override: int | None
) -> str:
    current_year, current_month, current_patch = _parse_existing_version(current_version)
    target_year = target_date.year
    target_month = target_date.month

    if patch_override is None:
        if (target_year, target_month) == (current_year, current_month):
            next_patch = current_patch + 1
        else:
            next_patch = 0
    else:
        next_patch = patch_override

    return f"{target_year}.{target_month}.{next_patch}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump pyproject.toml version using YYYY.M.x monthly patching",
    )
    parser.add_argument(
        "--date",
        help="Override date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--patch",
        type=int,
        help="Override patch number x in YYYY.M.x",
    )
    args = parser.parse_args()

    if args.patch is not None and args.patch < 0:
        raise RuntimeError("--patch must be >= 0")

    if args.date:
        target_date = dt.date.fromisoformat(args.date)
    else:
        target_date = dt.date.today()

    root = _project_root()
    pyproject_path = root / "pyproject.toml"
    current_version = tomllib.loads(pyproject_path.read_text())["project"]["version"]
    if not isinstance(current_version, str):
        raise RuntimeError("Could not read [project].version from pyproject.toml")

    new_version = _next_monthly_patch(
        current_version=current_version,
        target_date=target_date,
        patch_override=args.patch,
    )
    previous, updated = _replace_project_version(pyproject_path, new_version)
    print(f"Updated backend version: {previous} -> {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
