"""Product version helpers."""

from __future__ import annotations

import os
import re
import subprocess
import tomllib
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as metadata_version
from pathlib import Path

CALVER_PATTERN = re.compile(r"^\d{4}\.(?:[1-9]|1[0-2])\.\d+$")
RELEASE_VERSION_PATTERN = re.compile(r"^\d{4}\.(?:[1-9]|1[0-2])\.\d+(?:rc\d+)?$")


def _find_pyproject_path() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None


@lru_cache
def get_base_version() -> str:
    """Return canonical product version from project config or package metadata."""
    pyproject_path = _find_pyproject_path()
    if pyproject_path is not None:
        pyproject = tomllib.loads(pyproject_path.read_text())
        project = pyproject.get("project", {})
        value = project.get("version")
        if isinstance(value, str):
            return value

    try:
        return metadata_version("modelmeter")
    except PackageNotFoundError:
        return "0.0.0"


@lru_cache
def get_git_short_sha(length: int = 7) -> str | None:
    """Return a short git commit hash when available."""
    env_sha = os.getenv("MODELMETER_GIT_SHA", "").strip()
    if env_sha:
        return env_sha[:length]

    pyproject_path = _find_pyproject_path()
    if pyproject_path is None:
        return None

    repo_root = pyproject_path.parent
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return None

    try:
        result = subprocess.run(
            ["git", "rev-parse", f"--short={length}", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    value = result.stdout.strip()
    if value:
        return value
    return None


@lru_cache
def get_product_version() -> str:
    """Return display/runtime version as CalVer with optional short git hash."""
    base_version = get_base_version()
    short_sha = get_git_short_sha()
    if short_sha is None:
        return base_version
    return f"{base_version}+{short_sha}"


def is_calver(value: str) -> bool:
    """Return True when value matches the stable canonical CalVer format."""
    return CALVER_PATTERN.match(value) is not None


def is_release_version(value: str) -> bool:
    """Return True when value matches stable or rc release version format."""
    return RELEASE_VERSION_PATTERN.match(value) is not None
