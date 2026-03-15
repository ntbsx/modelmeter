#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="ntbsx/modelmeter"
GITHUB_API="https://api.github.com/repos/${PROJECT_PATH}"

VERSION=""
METHOD="auto"

usage() {
  cat <<'EOF'
Install ModelMeter from GitHub releases.

Usage:
  install.sh [--version X.Y.Z] [--method auto|pipx|pip]

Examples:
  ./scripts/install.sh
  ./scripts/install.sh --version 2026.3.13
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --method)
      METHOD="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$VERSION" ]]; then
  VERSION="${VERSION#v}"
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

resolve_latest_version() {
  curl -fsSL "${GITHUB_API}/releases/latest" | python3 -c '
import json, sys
release = json.load(sys.stdin)
tag = str(release.get("tag_name", "")).strip()
if not tag:
    raise SystemExit("Could not resolve latest release tag")
print(tag.lstrip("v"))
'
}

resolve_wheel_url() {
  local tag="$1"
  curl -fsSL "${GITHUB_API}/releases/tags/${tag}" | python3 -c '
import json
import sys

release = json.load(sys.stdin)
assets = release.get("assets", [])

for asset in assets:
    url = str(asset.get("browser_download_url", "")).strip()
    if url.endswith(".whl"):
        print(url)
        raise SystemExit(0)

raise SystemExit("No wheel release asset found for tag")
'
}

if [[ -z "$VERSION" ]]; then
  VERSION="$(resolve_latest_version)"
fi

TAG="v${VERSION}"
ARCHIVE_URL="https://github.com/${PROJECT_PATH}/archive/refs/tags/${TAG}.tar.gz"
WHEEL_URL=""

if WHEEL_URL="$(resolve_wheel_url "${TAG}" 2>/dev/null)"; then
  INSTALL_SPEC="${WHEEL_URL}"
  echo "Installing ModelMeter ${VERSION} from release wheel asset"
else
  INSTALL_SPEC="${ARCHIVE_URL}"
  echo "Wheel asset not found for ${TAG}; falling back to source archive"
fi

echo "Install source: ${INSTALL_SPEC}"

install_with_pipx() {
  if ! command -v pipx >/dev/null 2>&1; then
    return 1
  fi

  if pipx list --short | grep -qx modelmeter; then
    pipx reinstall --spec "$INSTALL_SPEC" modelmeter
  else
    pipx install "$INSTALL_SPEC"
  fi
}

install_with_pip() {
  python3 -m pip install --user --upgrade "$INSTALL_SPEC"
}

case "$METHOD" in
  auto)
    if ! install_with_pipx; then
      install_with_pip
    fi
    ;;
  pipx)
    install_with_pipx
    ;;
  pip)
    install_with_pip
    ;;
  *)
    echo "Invalid --method: ${METHOD}" >&2
    exit 1
    ;;
esac

if command -v modelmeter >/dev/null 2>&1; then
  echo "Installed: $(modelmeter --version)"
  echo "Run: modelmeter serve"
else
  echo "ModelMeter installed but not found on PATH yet."
  echo "If you used pip --user, ensure your user bin directory is on PATH."
fi
