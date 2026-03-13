"""Product version helpers."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as metadata_version
from pathlib import Path


def _find_pyproject_path() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return candidate
    return None


@lru_cache
def get_product_version() -> str:
    """Return the product version from installed metadata or project config."""
    try:
        return metadata_version("modelmeter")
    except PackageNotFoundError:
        pyproject_path = _find_pyproject_path()
        if pyproject_path is None:
            return "0.0.0"

        pyproject = tomllib.loads(pyproject_path.read_text())
        project = pyproject.get("project", {})
        value = project.get("version")
        if isinstance(value, str):
            return value
        return "0.0.0"
