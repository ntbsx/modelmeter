from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _read_backend_version(root: Path) -> str:
    pyproject_path = root / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text())
    project = pyproject.get("project", {})
    value = project.get("version")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("Could not read [project].version from pyproject.toml")
    return value


def _read_web_package_json(root: Path) -> tuple[Path, dict[str, object]]:
    package_path = root / "web" / "package.json"
    package_data = json.loads(package_path.read_text())
    if not isinstance(package_data, dict):
        raise RuntimeError("web/package.json must contain a JSON object")
    return package_path, package_data


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
