#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="ntbsdev/modelmeter"
PROJECT_PATH_ENCODED="ntbsdev%2Fmodelmeter"
GITLAB_API="https://gitlab.com/api/v4/projects/${PROJECT_PATH_ENCODED}"

VERSION=""
METHOD="auto"

usage() {
  cat <<'EOF'
Install ModelMeter from GitLab releases.

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
  curl -fsSL "${GITLAB_API}/releases/permalink/latest" | python3 -c '
import json, sys
release = json.load(sys.stdin)
tag = str(release.get("tag_name", "")).strip()
if not tag:
    raise SystemExit("Could not resolve latest release tag")
print(tag.lstrip("v"))
'
}

if [[ -z "$VERSION" ]]; then
  VERSION="$(resolve_latest_version)"
fi

TAG="v${VERSION}"
ARCHIVE_URL="https://gitlab.com/${PROJECT_PATH}/-/archive/${TAG}/modelmeter-${TAG}.tar.gz"

echo "Installing ModelMeter ${VERSION} from ${ARCHIVE_URL}"

install_with_pipx() {
  if ! command -v pipx >/dev/null 2>&1; then
    return 1
  fi

  if pipx list --short | grep -qx modelmeter; then
    pipx reinstall --spec "$ARCHIVE_URL" modelmeter
  else
    pipx install "$ARCHIVE_URL"
  fi
}

install_with_pip() {
  python3 -m pip install --user --upgrade "$ARCHIVE_URL"
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
