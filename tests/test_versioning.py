from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from modelmeter.common.version import (
    get_base_version,
    get_git_short_sha,
    get_product_version,
    is_calver,
)
from modelmeter.config.settings import AppSettings


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _pyproject_version(root: Path) -> str:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    version = pyproject["project"]["version"]
    assert isinstance(version, str)
    return version


def test_runtime_product_version_matches_pyproject() -> None:
    root = _project_root()
    expected = _pyproject_version(root)

    assert is_calver(expected)
    assert get_base_version() == expected
    assert AppSettings().app_version == expected


def test_runtime_product_version_includes_short_hash_when_available() -> None:
    base = get_base_version()
    runtime = get_product_version()
    short_sha = get_git_short_sha()

    if short_sha is None:
        assert runtime == base
    else:
        assert runtime == f"{base}+{short_sha}"
        assert re.fullmatch(r"[0-9a-f]{7}", short_sha) is not None


def test_frontend_version_matches_pyproject() -> None:
    root = _project_root()
    expected = _pyproject_version(root)
    web_package = json.loads((root / "web" / "package.json").read_text())

    assert web_package["version"] == expected
