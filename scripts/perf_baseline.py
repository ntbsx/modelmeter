from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import TypedDict

from fastapi.testclient import TestClient

from modelmeter.api.app import create_app


class AssetSize(TypedDict):
    name: str
    bytes: int


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _bundle_sizes(root: Path) -> dict[str, object]:
    dist_dir = root / "web" / "dist"
    if not dist_dir.exists():
        raise RuntimeError("web/dist not found. Run 'npm run --prefix web build' first.")

    asset_dir = dist_dir / "assets"
    files: list[AssetSize] = []
    total_bytes = 0
    for path in sorted(asset_dir.glob("*")):
        if not path.is_file():
            continue
        size = path.stat().st_size
        files.append({"name": path.name, "bytes": int(size)})
        total_bytes += size

    top: list[AssetSize] = sorted(
        files,
        key=lambda item: item["bytes"],
        reverse=True,
    )[:5]
    return {
        "asset_count": len(files),
        "total_bytes": total_bytes,
        "top_assets": top,
    }


def _health_latency() -> dict[str, float]:
    app = create_app()
    samples_ms: list[float] = []
    with TestClient(app) as client:
        for _ in range(30):
            start = time.perf_counter()
            response = client.get("/health")
            end = time.perf_counter()
            if response.status_code != 200:
                raise RuntimeError("/health latency probe failed")
            samples_ms.append((end - start) * 1000)

    return {
        "min_ms": round(min(samples_ms), 4),
        "avg_ms": round(statistics.mean(samples_ms), 4),
        "p95_ms": round(sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1], 4),
        "max_ms": round(max(samples_ms), 4),
    }


def main() -> int:
    root = _project_root()
    report = {
        "bundle": _bundle_sizes(root),
        "api": {"health": _health_latency()},
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
