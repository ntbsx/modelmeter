"""Release update checks and installer integration."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Literal, cast

from modelmeter.common.version import get_base_version
from modelmeter.config.settings import AppSettings
from modelmeter.core.models import UpdateCheckResponse

PROJECT_PATH = "ntbsdev/modelmeter"
PROJECT_PATH_ENCODED = "ntbsdev%2Fmodelmeter"
GITLAB_API = f"https://gitlab.com/api/v4/projects/{PROJECT_PATH_ENCODED}"


def _calver_key(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version '{value}'")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _is_newer_version(current: str, candidate: str) -> bool:
    try:
        return _calver_key(candidate) > _calver_key(current)
    except ValueError:
        return False


def _fetch_json(url: str, *, timeout_seconds: int) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "modelmeter/updater"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object response")
    return cast(dict[str, Any], payload)


def _resolve_latest_release(
    *, settings: AppSettings
) -> tuple[str | None, str | None, str | None, str | None]:
    """Return latest release details as (version, tag, web_url, error)."""
    try:
        payload = _fetch_json(
            settings.update_check_url,
            timeout_seconds=settings.update_check_timeout_seconds,
        )
    except (urllib.error.URLError, ValueError, TimeoutError) as exc:
        return None, None, None, str(exc)

    tag_name = payload.get("tag_name")
    if not isinstance(tag_name, str) or not tag_name.strip():
        return None, None, None, "Latest release payload missing tag_name"

    tag = tag_name.strip()
    version = tag.lstrip("v")
    web_url = payload.get("_links", {}).get("self")
    if not isinstance(web_url, str):
        web_url = payload.get("url") if isinstance(payload.get("url"), str) else None
    return version, tag, web_url, None


def check_for_updates(*, settings: AppSettings) -> UpdateCheckResponse:
    """Check for newer ModelMeter releases."""
    current_version = get_base_version()
    checked_at_ms = int(time.time() * 1000)
    if not settings.update_check_enabled:
        return UpdateCheckResponse(
            current_version=current_version,
            checked_at_ms=checked_at_ms,
            error="Update checks are disabled by configuration.",
        )

    latest_version, release_tag, release_url, error = _resolve_latest_release(settings=settings)
    if error is not None:
        return UpdateCheckResponse(
            current_version=current_version,
            checked_at_ms=checked_at_ms,
            error=error,
        )

    assert latest_version is not None
    return UpdateCheckResponse(
        current_version=current_version,
        latest_version=latest_version,
        update_available=_is_newer_version(current_version, latest_version),
        release_tag=release_tag,
        release_url=release_url,
        checked_at_ms=checked_at_ms,
    )


def _resolve_wheel_url(*, tag: str, timeout_seconds: int) -> str | None:
    payload = _fetch_json(
        f"{GITLAB_API}/releases/{tag}",
        timeout_seconds=timeout_seconds,
    )
    assets = payload.get("assets")
    if not isinstance(assets, dict):
        return None
    assets_map = cast(dict[str, Any], assets)
    links = assets_map.get("links")
    if not isinstance(links, list):
        return None

    for link_map in cast(list[dict[str, Any]], links):
        url = link_map.get("url")
        if isinstance(url, str) and url.endswith(".whl"):
            return url
    return None


def _resolve_install_spec(*, version: str, timeout_seconds: int) -> str:
    tag = f"v{version}"
    wheel_url = _resolve_wheel_url(tag=tag, timeout_seconds=timeout_seconds)
    if wheel_url is not None:
        return wheel_url
    return f"https://gitlab.com/{PROJECT_PATH}/-/archive/{tag}/modelmeter-{tag}.tar.gz"


def _run_install_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def apply_update(
    *,
    settings: AppSettings,
    version: str | None,
    method: Literal["auto", "pipx", "pip"],
    dry_run: bool,
) -> tuple[str, list[str]]:
    """Apply an update using selected install method."""
    target_version = version
    if target_version is None:
        check = check_for_updates(settings=settings)
        if check.latest_version is None:
            raise RuntimeError(check.error or "Unable to resolve latest release")
        target_version = check.latest_version

    spec = _resolve_install_spec(
        version=target_version,
        timeout_seconds=settings.update_check_timeout_seconds,
    )

    if method == "pipx":
        command = ["pipx", "install", "--force", spec]
    elif method == "pip":
        command = ["python3", "-m", "pip", "install", "--user", "--upgrade", spec]
    else:
        command = ["python3", "-m", "pip", "install", "--user", "--upgrade", spec]

    if dry_run:
        return spec, command

    _run_install_command(command)
    return spec, command
