from __future__ import annotations

import shutil
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    root = _project_root()
    source = root / "web" / "dist"
    target = root / "src" / "modelmeter" / "web_dist"

    if not source.exists():
        raise RuntimeError("web/dist not found. Run 'npm run --prefix web build' first.")

    if target.exists():
        shutil.rmtree(target)

    shutil.copytree(source, target)
    print(f"Copied web dist: {source} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
