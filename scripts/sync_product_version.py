from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path
from typing import cast

from modelmeter.common.version import is_calver


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_backend_version(root: Path) -> str:
    pyproject_path = root / "pyproject.toml"
    pyproject = cast(dict[str, object], tomllib.loads(pyproject_path.read_text()))
    project_data = pyproject.get("project", {})
    if not isinstance(project_data, dict):
        raise RuntimeError("[project] section must be a TOML object")
    project = cast(dict[str, object], project_data)
    value = project.get("version")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("Could not read [project].version from pyproject.toml")
    if not is_calver(value):
        raise RuntimeError(
            "[project].version must be CalVer in the format YYYY.M.D (example: 2026.3.13)",
        )
    return value


def _read_web_package_json(root: Path) -> tuple[Path, dict[str, object]]:
    package_path = root / "web" / "package.json"
    package_data: object = json.loads(package_path.read_text())
    if not isinstance(package_data, dict):
        raise RuntimeError("web/package.json must contain a JSON object")
    typed_package_data = cast(dict[str, object], package_data)
    return package_path, typed_package_data


def _write_package_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(f"{json.dumps(data, indent=2)}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync web/package.json version with pyproject.toml",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only and fail when versions differ",
    )
    args = parser.parse_args()

    root = _project_root()
    backend_version = _read_backend_version(root)
    package_path, package_data = _read_web_package_json(root)

    current_web_version = package_data.get("version")
    if not isinstance(current_web_version, str) or not current_web_version.strip():
        raise RuntimeError("web/package.json is missing a valid version string")

    if current_web_version == backend_version:
        print(f"Versions are in sync: {backend_version}")
        return 0

    if args.check:
        print(
            f"Version mismatch detected: backend={backend_version}, frontend={current_web_version}",
        )
        return 1

    package_data["version"] = backend_version
    _write_package_json(package_path, package_data)
    print(
        f"Updated web/package.json version: {current_web_version} -> {backend_version}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
