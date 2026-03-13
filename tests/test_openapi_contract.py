from __future__ import annotations

import hashlib
import json
from pathlib import Path

from modelmeter.api.app import create_app


def test_web_openapi_snapshot_is_current() -> None:
    snapshot_path = Path(__file__).resolve().parent.parent / "web" / "openapi.json"
    snapshot = json.loads(snapshot_path.read_text())

    app_schema = create_app().openapi()

    assert snapshot == app_schema


def test_generated_openapi_hash_matches_snapshot() -> None:
    root = Path(__file__).resolve().parent.parent
    snapshot_path = root / "web" / "openapi.json"
    hash_path = root / "web" / "src" / "generated" / "openapi.sha256"

    expected_hash = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
    generated_hash = hash_path.read_text().strip()

    assert generated_hash == expected_hash
