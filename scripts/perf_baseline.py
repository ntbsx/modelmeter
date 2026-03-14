from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path
from typing import TypedDict

from fastapi.testclient import TestClient

from modelmeter.api.app import create_app


class AssetSize(TypedDict):
    name: str
    bytes: int


class BundleReport(TypedDict):
    asset_count: int
    total_bytes: int
    top_assets: list[AssetSize]


class LatencyReport(TypedDict):
    min_ms: float
    avg_ms: float
    p95_ms: float
    max_ms: float


class BaselineReport(TypedDict, total=False):
    bundle: BundleReport
    api: dict[str, LatencyReport]
    thresholds: dict[str, dict[str, float]]


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _bundle_sizes(root: Path) -> BundleReport:
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


def _health_latency() -> LatencyReport:
    os.environ.setdefault("MODELMETER_PRICING_REMOTE_FALLBACK", "false")
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


def _create_live_fixture(db_path: Path) -> None:
    now_ms = int(time.time() * 1000)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE session ("
            "id TEXT PRIMARY KEY, "
            "project_id TEXT, "
            "title TEXT, "
            "directory TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "time_archived INTEGER"
            ")"
        )
        conn.execute("CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT, name TEXT)")
        conn.execute(
            "CREATE TABLE message ("
            "id TEXT PRIMARY KEY, "
            "session_id TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "data TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE part ("
            "id TEXT PRIMARY KEY, "
            "message_id TEXT, "
            "session_id TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "data TEXT"
            ")"
        )

        conn.execute(
            "INSERT INTO project (id, worktree, name) VALUES (?, ?, ?)",
            ("p1", "/tmp/perf", "perf-project"),
        )
        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "p1", "Perf Session", "/tmp/perf", now_ms, now_ms, None),
        )

        message_payload = {
            "role": "assistant",
            "modelID": "openai/gpt-5",
            "time": {"created": now_ms},
            "tokens": {
                "input": 100,
                "output": 20,
                "cache": {"read": 5, "write": 0},
            },
        }
        conn.execute(
            "INSERT INTO message "
            "(id, session_id, time_created, time_updated, data) VALUES (?, ?, ?, ?, ?)",
            ("m1", "s1", now_ms, now_ms, json.dumps(message_payload)),
        )

        step_payload = {
            "type": "step-finish",
            "tokens": {
                "input": 100,
                "output": 20,
                "cache": {"read": 5, "write": 0},
            },
        }
        tool_payload = {"type": "tool", "tool": "bash"}
        conn.execute(
            "INSERT INTO part "
            "(id, message_id, session_id, time_created, time_updated, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("pt1", "m1", "s1", now_ms, now_ms, json.dumps(step_payload)),
        )
        conn.execute(
            "INSERT INTO part "
            "(id, message_id, session_id, time_created, time_updated, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("pt2", "m1", "s1", now_ms, now_ms, json.dumps(tool_payload)),
        )


def _live_snapshot_latency() -> LatencyReport:
    os.environ.setdefault("MODELMETER_PRICING_REMOTE_FALLBACK", "false")
    app = create_app()
    samples_ms: list[float] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "opencode.db"
        _create_live_fixture(db_path)

        with TestClient(app) as client:
            for _ in range(30):
                start = time.perf_counter()
                response = client.get(
                    "/api/live/snapshot",
                    params={"db_path": str(db_path), "window_minutes": 60},
                )
                end = time.perf_counter()
                if response.status_code != 200:
                    raise RuntimeError("/api/live/snapshot latency probe failed")
                samples_ms.append((end - start) * 1000)

    return {
        "min_ms": round(min(samples_ms), 4),
        "avg_ms": round(statistics.mean(samples_ms), 4),
        "p95_ms": round(sorted(samples_ms)[int(len(samples_ms) * 0.95) - 1], 4),
        "max_ms": round(max(samples_ms), 4),
    }


def _largest_js_asset_kb(bundle: BundleReport) -> float:
    largest_bytes = 0
    for item in bundle["top_assets"]:
        if item["name"].endswith(".js"):
            largest_bytes = max(largest_bytes, item["bytes"])
    return largest_bytes / 1024


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate lightweight performance baseline report")
    parser.add_argument("--max-largest-js-kb", type=float, default=450.0)
    parser.add_argument("--max-health-avg-ms", type=float, default=20.0)
    parser.add_argument("--max-live-snapshot-avg-ms", type=float, default=60.0)
    parser.add_argument(
        "--fail-on-threshold",
        action="store_true",
        help="Fail with non-zero exit code when thresholds are exceeded",
    )
    args = parser.parse_args()

    root = _project_root()
    report: BaselineReport = {
        "bundle": _bundle_sizes(root),
        "api": {
            "health": _health_latency(),
            "live_snapshot": _live_snapshot_latency(),
        },
    }

    largest_js_kb = _largest_js_asset_kb(report["bundle"])
    health_avg = report["api"]["health"]["avg_ms"]
    live_avg = report["api"]["live_snapshot"]["avg_ms"]

    report["thresholds"] = {
        "largest_js_kb": {"limit": args.max_largest_js_kb, "actual": round(largest_js_kb, 3)},
        "health_avg_ms": {"limit": args.max_health_avg_ms, "actual": round(health_avg, 3)},
        "live_snapshot_avg_ms": {
            "limit": args.max_live_snapshot_avg_ms,
            "actual": round(live_avg, 3),
        },
    }

    print(json.dumps(report, indent=2))

    if args.fail_on_threshold:
        violations: list[str] = []
        if largest_js_kb > args.max_largest_js_kb:
            violations.append(
                "Largest JS bundle too large: "
                f"{largest_js_kb:.2f} KB > {args.max_largest_js_kb:.2f} KB",
            )
        if health_avg > args.max_health_avg_ms:
            violations.append(
                "/health average latency too high: "
                f"{health_avg:.2f} ms > {args.max_health_avg_ms:.2f} ms",
            )
        if live_avg > args.max_live_snapshot_avg_ms:
            violations.append(
                "live snapshot average latency too high: "
                f"{live_avg:.2f} ms > {args.max_live_snapshot_avg_ms:.2f} ms",
            )

        if violations:
            for violation in violations:
                print(f"PERF GUARDRAIL FAILED: {violation}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
