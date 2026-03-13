from __future__ import annotations

import argparse
import datetime as dt
import tomllib
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _calver_for_date(value: dt.date) -> str:
    return f"{value.year}.{value.month}.{value.day}"


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Stamp pyproject.toml with CalVer")
    parser.add_argument(
        "--date",
        help="Override date in YYYY-MM-DD format",
    )
    args = parser.parse_args()

    if args.date:
        target_date = dt.date.fromisoformat(args.date)
    else:
        target_date = dt.date.today()

    new_version = _calver_for_date(target_date)
    root = _project_root()
    pyproject_path = root / "pyproject.toml"
    previous, updated = _replace_project_version(pyproject_path, new_version)
    print(f"Updated backend version: {previous} -> {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
